from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.dependencies import get_db
from app.models import SportsEvent
from app.schemas import (
    BreakdownMetric,
    EventSummary,
    SimulationRequest,
    SimulationResponse,
    SportAnalyticsBreakdown,
    SportProfileResponse,
    ValueMatrixRequest,
)
from app.services.quant_engine import (
    SimulationConfig,
    build_value_matrix,
    reliability_score,
    simulate_matchup,
)
from app.services.sport_registry import SPORT_PROFILES, get_sport_profile, normalize_sport

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _simulation_config(request: SimulationRequest, defaults: dict | None = None) -> SimulationConfig:
    profile = get_sport_profile(request.sport)
    values = defaults or {}
    return SimulationConfig(
        home_mean=float(request.home_mean if request.home_mean is not None else values.get("home_mean", profile.default_home_mean)),
        away_mean=float(request.away_mean if request.away_mean is not None else values.get("away_mean", profile.default_away_mean)),
        home_sd=float(request.home_sd if request.home_sd is not None else values.get("home_sd", profile.default_home_sd)),
        away_sd=float(request.away_sd if request.away_sd is not None else values.get("away_sd", profile.default_away_sd)),
        correlation=float(request.correlation if request.correlation is not None else values.get("correlation", profile.default_correlation)),
        simulations=request.simulations,
        seed=request.seed,
        sport=normalize_sport(request.sport),
        sport_metrics=request.sport_metrics or values.get("sport_metrics", {}),
    )


@router.get("/sports", response_model=list[SportProfileResponse])
def sports_registry() -> list[SportProfileResponse]:
    return [
        SportProfileResponse(
            key=profile.key,
            label=profile.label,
            leagues=list(profile.leagues),
            markets=list(profile.markets),
            metrics=[{"key": key, "label": label} for key, label in profile.metrics],
        )
        for profile in SPORT_PROFILES.values()
    ]


@router.post("/simulate", response_model=SimulationResponse)
def simulate(request: SimulationRequest) -> SimulationResponse:
    result = simulate_matchup(_simulation_config(request))
    return SimulationResponse.model_validate(result)


@router.post("/value-matrix")
def value_matrix(request: ValueMatrixRequest) -> dict:
    rows = build_value_matrix(
        [quote.model_dump() for quote in request.quotes],
        request.model_probabilities,
        request.transaction_cost,
    )
    edge_message = "Significant model edge identified." if any(row["has_edge"] for row in rows) else "No significant model edge identified."
    return {"rows": rows, "edge_message": edge_message}


def _build_breakdown(sport: str, inputs: dict, simulation: dict, injuries: list) -> SportAnalyticsBreakdown:
    profile = get_sport_profile(sport)
    metrics = [
        BreakdownMetric(key=key, label=label, value=inputs.get(key))
        for key, label in profile.metrics
    ]
    metrics.extend(
        [
            BreakdownMetric(key="home_win_probability", label="Home win probability", value=simulation["home_win_probability"], unit="probability"),
            BreakdownMetric(key="away_win_probability", label="Away win probability", value=simulation["away_win_probability"], unit="probability"),
            BreakdownMetric(key="total_mean", label="Projected total", value=simulation["total_mean"]),
            BreakdownMetric(key="margin_mean", label="Projected margin", value=simulation["margin_mean"]),
        ]
    )
    loss_factors = [
        BreakdownMetric(
            key="injury",
            label=f"{injury.team}: {injury.player}",
            value=injury.status,
            unit="availability",
            risk="high" if injury.impact_points >= 2 else "medium",
        )
        for injury in injuries
    ]
    risk_keys = {"foul_trouble_risk", "quarterback_injury_impact", "bullpen_fatigue", "back_to_back_goalie_risk", "rotation_load", "card_suspension_risk", "fatigue_match_length", "precipitation", "wind_speed"}
    for metric in metrics:
        if metric.key in risk_keys and isinstance(metric.value, (int, float)) and float(metric.value) > 0:
            metric.risk = "high" if float(metric.value) >= 0.7 else "medium"
            loss_factors.append(metric)
    return SportAnalyticsBreakdown(
        sport=normalize_sport(sport),
        label=profile.label,
        leagues=list(profile.leagues),
        markets=list(profile.markets),
        metrics=metrics,
        loss_factors=loss_factors,
    )


@router.get("/breakdown", response_model=SportAnalyticsBreakdown)
def breakdown(
    sport: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> SportAnalyticsBreakdown:
    query = db.query(SportsEvent).options(joinedload(SportsEvent.injuries))
    if sport:
        query = query.filter(SportsEvent.sport == normalize_sport(sport))
    event = query.order_by(SportsEvent.start_time.asc()).first()
    if event is None:
        return _build_breakdown(normalize_sport(sport), {}, {"home_win_probability": 0.5, "away_win_probability": 0.5, "total_mean": 0.0, "margin_mean": 0.0}, [])
    inputs = event.model_inputs or {}
    request = SimulationRequest(sport=event.sport, sport_metrics=inputs)
    simulation = simulate_matchup(_simulation_config(request, inputs))
    return _build_breakdown(event.sport, inputs, simulation, event.injuries)


@router.get("/overview", response_model=EventSummary)
def overview(
    sport: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> EventSummary:
    query = db.query(SportsEvent).options(
        joinedload(SportsEvent.market_quotes), joinedload(SportsEvent.injuries)
    )
    if sport:
        query = query.filter(SportsEvent.sport == normalize_sport(sport))
    event = query.order_by(SportsEvent.start_time.asc()).first()
    if event is None:
        raise HTTPException(status_code=404, detail="No analytics events are available")

    inputs = event.model_inputs or {}
    request = SimulationRequest(
        sport=event.sport,
        home_mean=inputs.get("home_mean"),
        away_mean=inputs.get("away_mean"),
        home_sd=inputs.get("home_sd"),
        away_sd=inputs.get("away_sd"),
        correlation=inputs.get("correlation"),
        simulations=int(inputs.get("simulations", 10000)),
        seed=inputs.get("seed", 7),
        sport_metrics=inputs.get("sport_metrics", inputs),
    )
    simulation = simulate_matchup(_simulation_config(request, inputs))
    quotes = [
        {
            "sportsbook": quote.sportsbook,
            "market": quote.market,
            "selection": quote.selection,
            "american_odds": quote.american_odds,
            "line": quote.line,
        }
        for quote in event.market_quotes
    ]
    model_probabilities = {
        "home": simulation["home_win_probability"],
        "away": simulation["away_win_probability"],
        event.home_team: simulation["home_win_probability"],
        event.away_team: simulation["away_win_probability"],
    }
    matrix = build_value_matrix(quotes, model_probabilities)
    return EventSummary(
        id=event.id,
        sport=event.sport,
        league=event.league,
        home_team=event.home_team,
        away_team=event.away_team,
        start_time=event.start_time,
        venue=event.venue,
        weather=event.weather,
        injuries=[
            {"team": injury.team, "player": injury.player, "status": injury.status, "impact_points": injury.impact_points, "source": injury.source}
            for injury in event.injuries
        ],
        simulation=simulation,
        value_matrix=matrix,
        reliability_score=reliability_score(
            odds_age_seconds=120,
            injury_age_seconds=1800,
            sample_size=82,
            market_stability=0.82,
        ),
        edge_message="Significant model edge identified." if any(row["has_edge"] for row in matrix) else "No significant model edge identified.",
        sport_breakdown=_build_breakdown(event.sport, inputs, simulation, event.injuries),
    )
