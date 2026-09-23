from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SportsEvent(Base):
    __tablename__ = "sports_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sport: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    league: Mapped[str] = mapped_column(String(64), nullable=False)
    home_team: Mapped[str] = mapped_column(String(128), nullable=False)
    away_team: Mapped[str] = mapped_column(String(128), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    venue: Mapped[str | None] = mapped_column(String(160), nullable=True)
    weather: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    model_inputs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    home_team_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    away_team_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True, default="scheduled")

    market_quotes: Mapped[list["MarketQuote"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    injuries: Mapped[list["InjuryReport"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class MarketQuote(Base):
    __tablename__ = "market_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("sports_events.id", ondelete="CASCADE"), nullable=False, index=True)
    sportsbook: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[str] = mapped_column(String(32), nullable=False)
    selection: Mapped[str] = mapped_column(String(128), nullable=False)
    american_odds: Mapped[int] = mapped_column(Integer, nullable=False)
    line: Mapped[float | None] = mapped_column(Float, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    market_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contract_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    yes_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    no_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    liquidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    order_book: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    opening_american_odds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closing_american_odds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_closing: Mapped[bool | None] = mapped_column(nullable=True)

    event: Mapped[SportsEvent] = relationship(back_populates="market_quotes")


class InjuryReport(Base):
    __tablename__ = "injury_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("sports_events.id", ondelete="CASCADE"), nullable=False, index=True)
    team: Mapped[str] = mapped_column(String(128), nullable=False)
    player: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    impact_points: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source: Mapped[str] = mapped_column(String(96), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    event: Mapped[SportsEvent] = relationship(back_populates="injuries")


class SignalAlert(Base):
    __tablename__ = "signal_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("sports_events.id", ondelete="CASCADE"), nullable=True, index=True)
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(24), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_read: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    sport: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    league: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    abbreviation: Mapped[str | None] = mapped_column(String(16), nullable=True)
    aliases: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PredictionMarketSnapshot(Base):
    __tablename__ = "prediction_market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("sports_events.id", ondelete="SET NULL"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    market_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    question: Mapped[str] = mapped_column(String(240), nullable=False)
    outcome: Mapped[str] = mapped_column(String(128), nullable=False)
    share_price_cents: Mapped[float] = mapped_column(Float, nullable=False)
    bid_cents: Mapped[float | None] = mapped_column(Float, nullable=True)
    ask_cents: Mapped[float | None] = mapped_column(Float, nullable=True)
    liquidity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    volume_24h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    order_book: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    deep_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(96), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    bankroll: Mapped[float] = mapped_column(Float, nullable=False, default=10000.0)
    risk_limit: Mapped[float] = mapped_column(Float, nullable=False, default=0.05)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    positions: Mapped[list["Position"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("sports_events.id", ondelete="SET NULL"), nullable=True, index=True)
    instrument: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    selection: Mapped[str] = mapped_column(String(128), nullable=False)
    stake: Mapped[float] = mapped_column(Float, nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    model_probability: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    portfolio: Mapped[Portfolio] = relationship(back_populates="positions")


class InstitutionalSettings(Base):
    __tablename__ = "institutional_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_name: Mapped[str] = mapped_column(String(128), nullable=False, default="Institution")
    execution_mode: Mapped[str] = mapped_column(String(24), nullable=False, default="paper")
    risk_preset: Mapped[str] = mapped_column(String(24), nullable=False, default="balanced")
    max_trade_amount: Mapped[float] = mapped_column(Float, nullable=False, default=1000.0)
    authorized_admin_telegram_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    telegram_bot_token: Mapped[str | None] = mapped_column(String(256), nullable=True)
    polymarket_api_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    polymarket_api_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    polymarket_passphrase: Mapped[str | None] = mapped_column(String(256), nullable=True)
    wallet_private_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_security_pin: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class TradeExecution(Base):
    __tablename__ = "trade_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    instrument: Mapped[str] = mapped_column(String(32), nullable=False)
    condition_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    token_id: Mapped[str] = mapped_column(String(256), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    requested_price: Mapped[float] = mapped_column(Float, nullable=False)
    executed_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    size: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    external_order_id: Mapped[str | None] = mapped_column(String(256), nullable=True, unique=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    guardrail_result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    request_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    response_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TelegramAuthChallenge(Base):
    __tablename__ = "telegram_auth_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    challenge_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False, default="trade")
    pending_trade: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
