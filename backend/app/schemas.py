from datetime import datetime

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class SimulationRequest(BaseSchema):
    sport: str = "basketball"
    home_mean: float | None = Field(default=None, gt=0)
    away_mean: float | None = Field(default=None, gt=0)
    home_sd: float | None = Field(default=None, gt=0)
    away_sd: float | None = Field(default=None, gt=0)
    correlation: float | None = Field(default=None, ge=-0.99, le=0.99)
    simulations: int = Field(default=10000, ge=1000, le=100000)
    seed: int | None = 7
    sport_metrics: dict[str, Any] = Field(default_factory=dict)


class SimulationResponse(BaseSchema):
    simulations: int
    home_win_probability: float
    away_win_probability: float
    tie_probability: float
    margin_mean: float
    margin_sd: float
    total_mean: float
    margin_interval_90: list[float]
    total_interval_90: list[float]
    margin_histogram: list[dict[str, float]]
    total_histogram: list[dict[str, float]]


class MarketQuoteInput(BaseSchema):
    sportsbook: str
    market: str
    selection: str
    american_odds: int
    line: float | None = None


class ValueMatrixRequest(BaseSchema):
    sport: str = "basketball"
    quotes: list[MarketQuoteInput]
    model_probabilities: dict[str, float]
    transaction_cost: float = Field(default=0.0, ge=0, le=0.2)


class SportProfileResponse(BaseSchema):
    key: str
    label: str
    leagues: list[str]
    markets: list[str]
    metrics: list[dict[str, str]]


class BreakdownMetric(BaseSchema):
    key: str
    label: str
    value: float | str | bool | None
    unit: str | None = None
    risk: str | None = None


class SportAnalyticsBreakdown(BaseSchema):
    sport: str
    label: str
    leagues: list[str]
    markets: list[str]
    metrics: list[BreakdownMetric]
    loss_factors: list[BreakdownMetric]


class EventSummary(BaseSchema):
    id: int
    sport: str
    league: str
    home_team: str
    away_team: str
    start_time: datetime
    venue: str | None
    weather: dict | None
    injuries: list[dict]
    simulation: SimulationResponse
    value_matrix: list[dict]
    reliability_score: float
    edge_message: str
    sport_breakdown: SportAnalyticsBreakdown | None = None


class TeamSearchResult(BaseSchema):
    id: int
    name: str
    sport: str
    league: str
    abbreviation: str | None


class MarketSnapshotResponse(BaseSchema):
    provider: str
    market_id: str
    question: str
    outcome: str
    share_price_cents: float
    bid_cents: float | None
    ask_cents: float | None
    liquidity: float
    volume_24h: float
    order_book: dict
    deep_link: str | None
    captured_at: datetime
    sportsbook: str | None = None
    american_odds: int | None = None
    line: float | None = None
    model_probability: float | None = None
    synthetic_edge: float | None = None


class OpportunityResponse(BaseSchema):
    id: str
    event_id: int
    sport: str
    league: str
    matchup: str
    market: str
    selection: str
    provider: str
    price: str
    model_probability: float
    market_probability: float
    edge: float
    ev_percent: float
    confidence: float
    liquidity: float
    time_to_start_minutes: int
    polymarket_link: str | None
    sportsbook_link: str | None


class EventTerminalResponse(BaseSchema):
    event_id: int
    matchup: str
    sport: str
    league: str
    start_time: datetime
    status: str
    markets: list[MarketSnapshotResponse]
    clv: dict[str, float]
    model_performance: dict[str, float]


class PortfolioPositionResponse(BaseSchema):
    id: int
    instrument: str
    provider: str
    selection: str
    stake: float
    entry_price: float
    model_probability: float
    status: str
    unrealized_pnl: float
    risk_contribution: float


class PortfolioSummaryResponse(BaseSchema):
    portfolio_id: int
    name: str
    bankroll: float
    invested: float
    available_capital: float
    unrealized_pnl: float
    exposure_pct: float
    max_position_pct: float
    positions: list[PortfolioPositionResponse]
    risk_flags: list[str]


class SignalAlertResponse(BaseSchema):
    id: int
    event_id: int | None
    signal_type: str
    severity: str
    message: str
    payload: dict | None
    is_read: bool
    created_at: datetime


class SignalReadRequest(BaseSchema):
    is_read: bool = True


class InstitutionalSettingsResponse(BaseSchema):
    id: int
    organization_name: str
    execution_mode: str
    risk_preset: str
    max_trade_amount: float
    authorized_admin_telegram_ids: list[str]
    has_telegram_bot_token: bool
    has_polymarket_credentials: bool
    has_wallet_private_key: bool
    has_admin_security_pin: bool
    updated_at: datetime


class InstitutionalSettingsUpdate(BaseModel):
    organization_name: str | None = None
    execution_mode: str | None = None
    risk_preset: str | None = None
    max_trade_amount: float | None = None
    authorized_admin_telegram_ids: list[str] | None = None
    telegram_bot_token: str | None = None
    polymarket_api_key: str | None = None
    polymarket_api_secret: str | None = None
    polymarket_passphrase: str | None = None
    wallet_private_key: str | None = None
    admin_security_pin: str | None = None


class GuardrailResult(BaseSchema):
    passed: bool
    expected_value: float
    confidence: float
    liquidity: float
    minimum_liquidity: float
    reasons: list[str]


class TradeExecutionRequest(BaseModel):
    condition_id: str | None = None
    token_id: str
    side: str
    price: float
    size: float
    expected_value: float | None = None
    confidence: float | None = None
    minimum_liquidity: float | None = None
    admin_telegram_id: str | None = None
    security_pin: str | None = None


class TradeExecutionResponse(BaseSchema):
    id: int
    provider: str
    token_id: str
    side: str
    requested_price: float
    executed_price: float | None
    size: float
    status: str
    external_order_id: str | None
    failure_reason: str | None
    guardrail_result: GuardrailResult
    requested_at: datetime
    executed_at: datetime | None


class TradeHistoryItem(BaseSchema):
    id: int
    provider: str
    instrument: str
    condition_id: str | None
    token_id: str
    side: str
    requested_price: float
    executed_price: float | None
    size: float
    status: str
    external_order_id: str | None
    failure_reason: str | None
    guardrail_result: dict
    requested_at: datetime
    executed_at: datetime | None
