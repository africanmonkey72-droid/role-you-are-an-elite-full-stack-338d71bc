from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Iterable


@dataclass(frozen=True)
class SimulationConfig:
    home_mean: float
    away_mean: float
    home_sd: float = 10.5
    away_sd: float = 10.5
    correlation: float = 0.18
    simulations: int = 10000
    seed: int | None = 7
    sport: str = "basketball"
    sport_metrics: dict[str, float | str | bool] | None = None


def american_to_decimal(american_odds: int) -> float:
    if american_odds == 0:
        raise ValueError("American odds cannot be zero")
    return 1 + (american_odds / 100 if american_odds > 0 else 100 / abs(american_odds))


def decimal_to_american(decimal_odds: float) -> int:
    if decimal_odds <= 1:
        raise ValueError("Decimal odds must be greater than 1")
    return round((decimal_odds - 1) * 100) if decimal_odds >= 2 else round(-100 / (decimal_odds - 1))


def implied_probability(american_odds: int) -> float:
    decimal = american_to_decimal(american_odds)
    return 1 / decimal


def prediction_market_probability(share_price_cents: float) -> float:
    """Convert a 0-100 cent prediction-market price into a bounded probability."""
    return max(0.001, min(0.999, float(share_price_cents) / 100.0))


def devig_probabilities(probabilities: Iterable[float]) -> list[float]:
    values = [max(0.0, float(value)) for value in probabilities]
    total = sum(values)
    if total <= 0:
        raise ValueError("At least one implied probability must be positive")
    return [value / total for value in values]


def expected_value(model_probability: float, decimal_odds: float, transaction_cost: float = 0.0) -> float:
    return (model_probability * decimal_odds) - 1 - transaction_cost


def reliability_score(*, odds_age_seconds: float, injury_age_seconds: float, sample_size: int, market_stability: float) -> float:
    recency = max(0.0, 1 - odds_age_seconds / 3600) * 0.45 + max(0.0, 1 - injury_age_seconds / 21600) * 0.25
    sample_component = min(1.0, math.log1p(max(0, sample_size)) / math.log1p(100)) * 0.2
    stability_component = max(0.0, min(1.0, market_stability)) * 0.1
    return round(100 * min(1.0, recency + sample_component + stability_component), 1)


def _correlated_normals(rng: random.Random, correlation: float) -> tuple[float, float]:
    z1 = rng.gauss(0, 1)
    independent = rng.gauss(0, 1)
    z2 = correlation * z1 + math.sqrt(max(0.0, 1 - correlation**2)) * independent
    return z1, z2


def _metric_number(metrics: dict[str, float | str | bool], key: str) -> float | None:
    value = metrics.get(key)
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _adjusted_config(config: SimulationConfig) -> tuple[float, float, float, float]:
    metrics = config.sport_metrics or {}
    home_mean = config.home_mean
    away_mean = config.away_mean
    home_sd = config.home_sd
    away_sd = config.away_sd

    if config.sport in {"basketball", "football"}:
        home_mean += (_metric_number(metrics, "offensive_rating") or 0.0) * 0.04
        away_mean += (_metric_number(metrics, "away_offensive_rating") or 0.0) * 0.04
        home_mean -= (_metric_number(metrics, "defensive_rating") or 0.0) * 0.02
        away_mean -= (_metric_number(metrics, "away_defensive_rating") or 0.0) * 0.02
    elif config.sport == "baseball":
        home_mean += ((_metric_number(metrics, "park_factor") or 100.0) - 100.0) * 0.01
        away_mean += ((_metric_number(metrics, "away_park_factor") or 100.0) - 100.0) * 0.01
        home_sd *= 1.0 + min(0.4, max(0.0, (_metric_number(metrics, "bullpen_fatigue") or 0.0) / 100.0))
        away_sd *= 1.0 + min(0.4, max(0.0, (_metric_number(metrics, "away_bullpen_fatigue") or 0.0) / 100.0))
    elif config.sport == "hockey":
        home_mean += (_metric_number(metrics, "goaltender_gsax") or 0.0) * 0.03
        away_mean += (_metric_number(metrics, "away_goaltender_gsax") or 0.0) * 0.03
    elif config.sport == "soccer":
        home_mean += (_metric_number(metrics, "xg") or 0.0) * 0.08
        away_mean += (_metric_number(metrics, "away_xg") or 0.0) * 0.08
    elif config.sport == "tennis":
        home_mean += (_metric_number(metrics, "first_serve_win_rate") or 0.0) * 0.01
        away_mean += (_metric_number(metrics, "away_first_serve_win_rate") or 0.0) * 0.01
    elif config.sport == "mma":
        home_mean += (_metric_number(metrics, "striking_accuracy") or 0.0) * 0.005
        away_mean += (_metric_number(metrics, "away_striking_accuracy") or 0.0) * 0.005

    travel = _metric_number(metrics, "travel_distance") or 0.0
    altitude = _metric_number(metrics, "altitude") or 0.0
    home_mean -= max(0.0, travel) * 0.00002
    away_mean -= max(0.0, altitude) * 0.0005
    return max(0.01, home_mean), max(0.01, away_mean), max(0.05, home_sd), max(0.05, away_sd)


def simulate_matchup(config: SimulationConfig) -> dict:
    if config.simulations < 1000:
        raise ValueError("Use at least 1,000 simulations for stable intervals")
    rng = random.Random(config.seed)
    home_mean, away_mean, home_sd, away_sd = _adjusted_config(config)
    margins: list[float] = []
    totals: list[float] = []
    home_wins = 0
    ties = 0

    for _ in range(config.simulations):
        z_home, z_away = _correlated_normals(rng, config.correlation)
        home_score = max(0.0, home_mean + home_sd * z_home)
        away_score = max(0.0, away_mean + away_sd * z_away)
        margin = home_score - away_score
        total = home_score + away_score
        margins.append(margin)
        totals.append(total)
        home_wins += margin > 0.05
        ties += abs(margin) <= 0.05

    margins.sort()
    totals.sort()
    home_probability = home_wins / config.simulations
    away_probability = (config.simulations - home_wins - ties) / config.simulations
    return {
        "simulations": config.simulations,
        "home_win_probability": round(home_probability, 4),
        "away_win_probability": round(away_probability, 4),
        "tie_probability": round(ties / config.simulations, 4),
        "margin_mean": round(mean(margins), 2),
        "margin_sd": round(pstdev(margins), 2),
        "total_mean": round(mean(totals), 2),
        "margin_interval_90": [round(margins[int(0.05 * len(margins))], 2), round(margins[int(0.95 * len(margins))], 2)],
        "total_interval_90": [round(totals[int(0.05 * len(totals))], 2), round(totals[int(0.95 * len(totals))], 2)],
        "margin_histogram": _histogram(margins, bins=12),
        "total_histogram": _histogram(totals, bins=12),
    }


def _histogram(values: list[float], bins: int) -> list[dict[str, float]]:
    minimum, maximum = min(values), max(values)
    width = max((maximum - minimum) / bins, 1.0)
    counts = [0] * bins
    for value in values:
        index = min(bins - 1, int((value - minimum) / width))
        counts[index] += 1
    return [
        {"bucket": round(minimum + (index + 0.5) * width, 2), "probability": round(count / len(values), 5)}
        for index, count in enumerate(counts)
    ]


def build_value_matrix(quotes: list[dict], model_probabilities: dict[str, float], transaction_cost: float = 0.0) -> list[dict]:
    grouped: dict[str, list[float]] = {}
    for quote in quotes:
        grouped.setdefault(quote["market"], []).append(implied_probability(quote["american_odds"]))

    market_fair: dict[str, dict[str, float]] = {}
    for market, probabilities in grouped.items():
        market_fair[market] = {str(index): value for index, value in enumerate(devig_probabilities(probabilities))}

    rows = []
    market_indexes: dict[str, int] = {}
    for quote in quotes:
        market_index = market_indexes.get(quote["market"], 0)
        market_indexes[quote["market"]] = market_index + 1
        market_prob = market_fair[quote["market"]][str(market_index)]
        model_probability = model_probabilities.get(quote["selection"], 0.0)
        decimal = american_to_decimal(quote["american_odds"])
        ev = expected_value(model_probability, decimal, transaction_cost)
        rows.append({
            **quote,
            "decimal_odds": round(decimal, 3),
            "vig_adjusted_probability": round(market_prob, 4),
            "model_probability": round(model_probability, 4),
            "fair_decimal_odds": round(1 / model_probability, 3) if model_probability > 0 else None,
            "fair_american_odds": decimal_to_american(1 / model_probability) if model_probability > 0 else None,
            "probability_edge": round(model_probability - market_prob, 4),
            "ev_percent": round(ev * 100, 2),
            "has_edge": ev > 0.02 and model_probability - market_prob > 0.015,
        })
    return rows
