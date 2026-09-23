from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.dependencies import get_db
from app.models import (
    InstitutionalSettings,
    MarketQuote,
    Portfolio,
    PredictionMarketSnapshot,
    SignalAlert,
    SportsEvent,
    Team,
    TelegramAuthChallenge,
    TradeExecution,
)
from app.schemas import (
    EventTerminalResponse,
    GuardrailResult,
    InstitutionalSettingsResponse,
    InstitutionalSettingsUpdate,
    MarketSnapshotResponse,
    OpportunityResponse,
    PortfolioPositionResponse,
    PortfolioSummaryResponse,
    SignalAlertResponse,
    SignalReadRequest,
    TeamSearchResult,
    TradeExecutionRequest,
    TradeExecutionResponse,
    TradeHistoryItem,
)
from app.services.institutional import (
    create_trade_challenge,
    get_or_create_settings,
    guardrail_decision,
    is_authorized_admin,
    public_settings,
    telegram_secret_is_valid,
    validate_risk_preset,
    verify_trade_challenge,
)
from app.services.polymarket import read_live_market, submit_limit_order
from app.services.quant_engine import american_to_decimal, implied_probability

router = APIRouter(prefix="/institutional", tags=["institutional"])


def _market_probability(american_odds: int) -> float:
    return float(implied_probability(american_odds))


def _prediction_probability(cents: float) -> float:
    return max(0.001, min(0.999, float(cents) / 100.0))


def _normalize_provider(provider: str) -> str:
    return {"poly": "polymarket", "polymarket gamma": "polymarket", "kalshi exchange": "kalshi", "books": "sportsbook"}.get(provider.strip().lower(), provider.strip().lower())


def _team_matches(event: SportsEvent, term: str, team: Team | None = None) -> bool:
    needle = term.strip().lower()
    names = [event.home_team, event.away_team]
    if team:
        names.extend([team.name, team.abbreviation or "", *(team.aliases or [])])
    return any(needle in name.lower() for name in names if name)


def _sportsbook_link(event: SportsEvent, selection: str) -> str:
    return f"https://sportsbook.example.com/events/{event.id}?selection={quote(selection)}"


def _provider_link(provider: str, market_id: str) -> str | None:
    normalized = _normalize_provider(provider)
    if normalized == "polymarket":
        return f"https://polymarket.com/event/{quote(market_id)}"
    if normalized == "kalshi":
        return f"https://kalshi.com/markets/{quote(market_id)}"
    return None


def _event_model_probability(event: SportsEvent, outcome: str) -> float:
    inputs = event.model_inputs or {}
    keyed = inputs.get("outcome_probabilities")
    if isinstance(keyed, dict) and outcome in keyed:
        return max(0.001, min(0.999, float(keyed[outcome])))
    home_probability = float(inputs.get("home_win_probability", inputs.get("home_probability", 0.58)))
    normalized = outcome.strip().lower()
    if normalized in {event.home_team.lower(), "home", "yes", "over"}:
        return max(0.001, min(0.999, home_probability))
    if normalized in {event.away_team.lower(), "away", "no", "under"}:
        return max(0.001, min(0.999, 1.0 - home_probability))
    return max(0.001, min(0.999, float(inputs.get("model_probability", 0.5))))


def _snapshot_response(snapshot: PredictionMarketSnapshot, event: SportsEvent | None = None) -> MarketSnapshotResponse:
    model_probability = _event_model_probability(event, snapshot.outcome) if event else None
    market_probability = _prediction_probability(snapshot.share_price_cents)
    return MarketSnapshotResponse(
        provider=_normalize_provider(snapshot.provider), market_id=snapshot.market_id, question=snapshot.question,
        outcome=snapshot.outcome, share_price_cents=snapshot.share_price_cents, bid_cents=snapshot.bid_cents,
        ask_cents=snapshot.ask_cents, liquidity=snapshot.liquidity, volume_24h=snapshot.volume_24h,
        order_book=snapshot.order_book or {}, deep_link=snapshot.deep_link or _provider_link(snapshot.provider, snapshot.market_id),
        captured_at=snapshot.captured_at, model_probability=model_probability,
        synthetic_edge=(model_probability - market_probability) if model_probability is not None else None,
    )


def _clv_metrics(event: SportsEvent) -> dict[str, float]:
    quotes = [quote for quote in event.market_quotes if quote.opening_american_odds and quote.closing_american_odds]
    if not quotes:
        return {"closing_line_value_pct": 0.0, "sample_size": 0.0}
    values = [(_market_probability(q.opening_american_odds or q.american_odds) - _market_probability(q.closing_american_odds or q.american_odds)) * 100 for q in quotes]
    return {"closing_line_value_pct": round(sum(values) / len(values), 2), "sample_size": float(len(values))}


@router.get("/teams/search", response_model=list[TeamSearchResult])
def search_teams(q: str = Query(default="", min_length=0, max_length=80), sport: str | None = Query(default=None), db: Session = Depends(get_db)) -> list[TeamSearchResult]:
    teams = db.query(Team).order_by(Team.name.asc()).limit(200).all()
    if q.strip():
        needle = q.strip().lower()
        teams = [team for team in teams if needle in team.name.lower() or needle in (team.abbreviation or "").lower() or any(needle in alias.lower() for alias in (team.aliases or []))]
    if sport:
        teams = [team for team in teams if team.sport.lower() == sport.lower()]
    return [TeamSearchResult.model_validate(team) for team in teams[:25]]


@router.get("/markets", response_model=list[MarketSnapshotResponse])
def live_markets(sport: str | None = Query(default=None), provider: str | None = Query(default=None), db: Session = Depends(get_db)) -> list[MarketSnapshotResponse]:
    query = db.query(PredictionMarketSnapshot).join(SportsEvent, isouter=True)
    if sport:
        query = query.filter(SportsEvent.sport == sport.lower())
    if provider:
        query = query.filter(PredictionMarketSnapshot.provider == _normalize_provider(provider))
    snapshots = query.order_by(PredictionMarketSnapshot.captured_at.desc()).limit(100).all()
    event_ids = [snapshot.event_id for snapshot in snapshots if snapshot.event_id]
    events = {event.id: event for event in db.query(SportsEvent).filter(SportsEvent.id.in_(event_ids)).all()} if event_ids else {}
    return [_snapshot_response(snapshot, events.get(snapshot.event_id)) for snapshot in snapshots]


@router.get("/opportunities", response_model=list[OpportunityResponse])
def top_opportunities(sport: str | None = Query(default=None), minimum_edge: float = Query(default=0.02, ge=0, le=1), db: Session = Depends(get_db)) -> list[OpportunityResponse]:
    query = db.query(SportsEvent).options(joinedload(SportsEvent.market_quotes))
    if sport:
        query = query.filter(SportsEvent.sport == sport.lower())
    events = query.order_by(SportsEvent.start_time.asc()).limit(250).all()
    results: list[OpportunityResponse] = []
    now = datetime.now(timezone.utc)
    for event in events:
        minutes = max(0, int((event.start_time - now).total_seconds() // 60))
        for quote in event.market_quotes:
            model_probability = _event_model_probability(event, quote.selection)
            market_probability = _market_probability(quote.american_odds)
            edge = model_probability - market_probability
            if edge < minimum_edge:
                continue
            results.append(OpportunityResponse(
                id=f"book-{quote.id}", event_id=event.id, sport=event.sport, league=event.league,
                matchup=f"{event.home_team} vs. {event.away_team}", market=quote.market, selection=quote.selection,
                provider=quote.sportsbook, price=f"{quote.american_odds:+d}", model_probability=round(model_probability, 4),
                market_probability=round(market_probability, 4), edge=round(edge, 4),
                ev_percent=round(((model_probability * american_to_decimal(quote.american_odds)) - 1) * 100, 2),
                confidence=round(min(0.99, 0.55 + edge * 1.5), 3), liquidity=float(quote.liquidity or (quote.raw_payload or {}).get("liquidity", 0)),
                time_to_start_minutes=minutes, polymarket_link=None, sportsbook_link=_sportsbook_link(event, quote.selection),
            ))
        for snapshot in db.query(PredictionMarketSnapshot).filter(PredictionMarketSnapshot.event_id == event.id).all():
            model_probability = _event_model_probability(event, snapshot.outcome)
            market_probability = _prediction_probability(snapshot.share_price_cents)
            edge = model_probability - market_probability
            if edge < minimum_edge:
                continue
            results.append(OpportunityResponse(
                id=f"{_normalize_provider(snapshot.provider)}-{snapshot.id}", event_id=event.id, sport=event.sport, league=event.league,
                matchup=f"{event.home_team} vs. {event.away_team}", market="prediction_market", selection=snapshot.outcome,
                provider=_normalize_provider(snapshot.provider), price=f"{snapshot.share_price_cents:.1f}¢", model_probability=round(model_probability, 4),
                market_probability=round(market_probability, 4), edge=round(edge, 4), ev_percent=round((model_probability / market_probability - 1) * 100, 2),
                confidence=round(min(0.99, 0.55 + edge * 1.5), 3), liquidity=float(snapshot.liquidity), time_to_start_minutes=minutes,
                polymarket_link=_provider_link(snapshot.provider, snapshot.market_id) if _normalize_provider(snapshot.provider) == "polymarket" else None,
                sportsbook_link=_sportsbook_link(event, snapshot.outcome),
            ))
    return sorted(results, key=lambda item: (item.ev_percent, item.confidence), reverse=True)[:50]


@router.get("/teams/{team_name}/terminal", response_model=list[EventTerminalResponse])
def team_terminal(team_name: str, db: Session = Depends(get_db)) -> list[EventTerminalResponse]:
    team = db.query(Team).filter(Team.name.ilike(team_name)).first()
    events = db.query(SportsEvent).options(joinedload(SportsEvent.market_quotes)).order_by(SportsEvent.start_time.asc()).limit(250).all()
    response = []
    for event in [item for item in events if _team_matches(item, team_name, team)]:
        markets = []
        for quote in event.market_quotes:
            market_probability = _market_probability(quote.american_odds)
            markets.append(MarketSnapshotResponse(
                provider=quote.sportsbook, market_id=str(quote.id), question=f"{event.home_team} vs. {event.away_team}", outcome=quote.selection,
                share_price_cents=market_probability * 100, bid_cents=None, ask_cents=None, liquidity=float(quote.liquidity or 0), volume_24h=0,
                order_book=quote.order_book or {}, deep_link=_sportsbook_link(event, quote.selection), captured_at=quote.captured_at,
                sportsbook=quote.sportsbook, american_odds=quote.american_odds, line=quote.line,
                model_probability=_event_model_probability(event, quote.selection), synthetic_edge=_event_model_probability(event, quote.selection) - market_probability,
            ))
        markets.extend(_snapshot_response(snapshot, event) for snapshot in db.query(PredictionMarketSnapshot).filter(PredictionMarketSnapshot.event_id == event.id).limit(100).all())
        inputs = event.model_inputs or {}
        response.append(EventTerminalResponse(
            event_id=event.id, matchup=f"{event.home_team} vs. {event.away_team}", sport=event.sport, league=event.league,
            start_time=event.start_time, status=event.status or "scheduled", markets=markets, clv=_clv_metrics(event),
            model_performance={"brier_score": float(inputs.get("brier_score", 0.0)), "calibration_pct": float(inputs.get("calibration_pct", 0.0)), "roi_pct": float(inputs.get("roi_pct", 0.0))},
        ))
    return response


@router.get("/signals", response_model=list[SignalAlertResponse])
def list_signals(unread_only: bool = Query(default=False), severity: str | None = Query(default=None), db: Session = Depends(get_db)) -> list[SignalAlertResponse]:
    query = db.query(SignalAlert)
    if unread_only:
        query = query.filter(SignalAlert.is_read.is_(False))
    if severity:
        query = query.filter(SignalAlert.severity == severity.lower())
    return [SignalAlertResponse.model_validate(alert) for alert in query.order_by(SignalAlert.created_at.desc()).limit(100).all()]


@router.patch("/signals/{signal_id}/read", response_model=SignalAlertResponse)
def mark_signal_read(signal_id: int, payload: SignalReadRequest, db: Session = Depends(get_db)) -> SignalAlertResponse:
    alert = db.query(SignalAlert).filter(SignalAlert.id == signal_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    alert.is_read = payload.is_read
    db.commit()
    db.refresh(alert)
    return SignalAlertResponse.model_validate(alert)


@router.get("/portfolio/summary", response_model=PortfolioSummaryResponse)
def portfolio_summary(db: Session = Depends(get_db)) -> PortfolioSummaryResponse:
    portfolio = db.query(Portfolio).options(joinedload(Portfolio.positions)).order_by(Portfolio.id.asc()).first()
    if portfolio is None:
        return PortfolioSummaryResponse(portfolio_id=0, name="Research portfolio", bankroll=10000, invested=0, available_capital=10000, unrealized_pnl=0, exposure_pct=0, max_position_pct=5, positions=[], risk_flags=["No live positions are currently recorded."])
    invested = sum(position.stake for position in portfolio.positions if position.status == "open")
    rows = []
    for position in portfolio.positions:
        pnl = position.stake * (0.5 - position.entry_price / 100) if position.instrument in {"polymarket", "kalshi", "prediction_market"} else position.stake * (position.model_probability * max(position.entry_price - 1, 0) - (1 - position.model_probability))
        rows.append(PortfolioPositionResponse(id=position.id, instrument=position.instrument, provider=position.provider, selection=position.selection, stake=position.stake, entry_price=position.entry_price, model_probability=position.model_probability, status=position.status, unrealized_pnl=round(pnl, 2), risk_contribution=round(position.stake / max(portfolio.bankroll, 1) * 100, 2)))
    exposure = invested / max(portfolio.bankroll, 1) * 100
    flags = ["Gross exposure is above the configured risk limit."] if exposure > portfolio.risk_limit * 100 else ["Portfolio exposure is within configured limits."]
    return PortfolioSummaryResponse(portfolio_id=portfolio.id, name=portfolio.name, bankroll=portfolio.bankroll, invested=round(invested, 2), available_capital=round(portfolio.bankroll - invested, 2), unrealized_pnl=round(sum(row.unrealized_pnl for row in rows), 2), exposure_pct=round(exposure, 2), max_position_pct=portfolio.risk_limit * 100, positions=rows, risk_flags=flags)


def _settings_response(settings: InstitutionalSettings) -> InstitutionalSettingsResponse:
    return InstitutionalSettingsResponse(**public_settings(settings))


def _trade_response(trade: TradeExecution) -> TradeExecutionResponse:
    return TradeExecutionResponse(
        id=trade.id, provider=trade.provider, token_id=trade.token_id, side=trade.side,
        requested_price=trade.requested_price, executed_price=trade.executed_price, size=trade.size,
        status=trade.status, external_order_id=trade.external_order_id, failure_reason=trade.failure_reason,
        guardrail_result=GuardrailResult(**trade.guardrail_result), requested_at=trade.requested_at,
        executed_at=trade.executed_at,
    )


def _execute_trade(db: Session, settings: InstitutionalSettings, request: TradeExecutionRequest) -> TradeExecution:
    side = request.side.upper()
    if side not in {"BUY", "SELL"} or not (0 < request.price < 1) or request.size <= 0:
        raise HTTPException(status_code=422, detail="Trade side, price, or size is invalid.")
    live = read_live_market(settings, request.token_id, side, request.size)
    shift = abs(live["price"] - request.price) if live["price"] else None
    decision = guardrail_decision(settings, expected_value=request.expected_value, confidence=request.confidence, liquidity=live["liquidity"], requested_size=request.size, price_shift=shift)
    trade = TradeExecution(provider="polymarket", instrument="prediction_market", condition_id=request.condition_id, token_id=request.token_id, side=side, requested_price=request.price, size=request.size, status="pending", guardrail_result=decision, request_payload=request.model_dump(exclude={"security_pin"}))
    db.add(trade)
    db.commit()
    db.refresh(trade)
    if not decision["passed"] or (shift is not None and shift > 0.02):
        trade.status = "cancelled"
        trade.failure_reason = "Trade canceled: Odds shifted or market liquidity is too low."
    elif settings.execution_mode == "paper":
        trade.status = "filled"
        trade.executed_price = live["price"] or request.price
        trade.external_order_id = f"paper-{trade.id}"
        trade.executed_at = datetime.now(timezone.utc)
    else:
        try:
            submitted = submit_limit_order(settings, request.token_id, side, request.price, request.size)
            trade.status = "submitted"
            trade.executed_price = request.price
            trade.external_order_id = submitted.get("order_id")
            trade.response_payload = submitted.get("response")
            trade.executed_at = submitted.get("executed_at")
        except Exception:
            trade.status = "failed"
            trade.failure_reason = "Polymarket rejected the order."
    db.commit()
    db.refresh(trade)
    return trade


@router.get("/settings", response_model=InstitutionalSettingsResponse)
def get_institutional_settings(db: Session = Depends(get_db)):
    return _settings_response(get_or_create_settings(db))


@router.patch("/settings", response_model=InstitutionalSettingsResponse)
def update_institutional_settings(payload: InstitutionalSettingsUpdate, db: Session = Depends(get_db), admin_id: str | None = Header(default=None, alias="X-Admin-Telegram-ID")):
    settings = get_or_create_settings(db)
    if settings.authorized_admin_telegram_ids and not is_authorized_admin(settings, admin_id):
        raise HTTPException(status_code=403, detail="Authorized admin Telegram ID required.")
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("risk_preset") is not None:
        updates["risk_preset"] = validate_risk_preset(updates["risk_preset"])
    if updates.get("execution_mode") not in {None, "paper", "live"}:
        raise HTTPException(status_code=422, detail="Execution mode must be paper or live.")
    if updates.get("max_trade_amount") is not None and updates["max_trade_amount"] <= 0:
        raise HTTPException(status_code=422, detail="Maximum trade amount must be positive.")
    for field, value in updates.items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return _settings_response(settings)


@router.post("/trade/execute", response_model=TradeExecutionResponse)
def execute_institutional_trade(request: TradeExecutionRequest, db: Session = Depends(get_db), admin_id: str | None = Header(default=None, alias="X-Admin-Telegram-ID"), header_pin: str | None = Header(default=None, alias="X-Admin-Security-Pin")):
    settings = get_or_create_settings(db)
    effective_admin = request.admin_telegram_id or admin_id
    if not is_authorized_admin(settings, effective_admin):
        raise HTTPException(status_code=403, detail="This action is restricted to authorized Telegram admins.")
    if not (request.security_pin or header_pin) or (request.security_pin or header_pin) != settings.admin_security_pin:
        raise HTTPException(status_code=403, detail="Security passcode is required for trade execution.")
    return _trade_response(_execute_trade(db, settings, request))


@router.get("/trades", response_model=list[TradeHistoryItem])
def get_trade_history(limit: int = Query(default=50, ge=1, le=200), status: str | None = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(TradeExecution).order_by(TradeExecution.requested_at.desc())
    if status:
        query = query.filter(TradeExecution.status == status)
    return query.limit(limit).all()


def _telegram_send(settings: InstitutionalSettings, chat_id: str | int, text: str, markup: dict | None = None) -> None:
    if not settings.telegram_bot_token:
        return
    import httpx
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if markup:
        payload["reply_markup"] = markup
    try:
        httpx.post(f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage", json=payload, timeout=10)
    except httpx.HTTPError:
        pass


def _alert_text(alert: SignalAlert) -> str:
    payload = alert.payload or {}
    lines = [alert.message]
    for label, key in [("Selection", "selection"), ("Market", "provider"), ("Edge", "edge"), ("Confidence", "confidence"), ("Expected value", "expected_value")]:
        if payload.get(key) is not None:
            value = payload[key]
            value = f"{float(value):.1%}" if key in {"edge", "confidence", "expected_value"} else value
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def _alert_markup(alert_id: int) -> dict:
    return {"inline_keyboard": [[{"text": "⚡ Buy $25", "callback_data": f"buy:{alert_id}:25"}, {"text": "⚡ Buy $50", "callback_data": f"buy:{alert_id}:50"}, {"text": "⚡ Buy $100", "callback_data": f"buy:{alert_id}:100"}], [{"text": "✏️ Custom Buy", "callback_data": f"custom:{alert_id}"}, {"text": "💡 Explain This Play", "callback_data": f"explain:{alert_id}"}, {"text": "❌ Dismiss", "callback_data": f"dismiss:{alert_id}"}]]}


def _explain_alert(alert: SignalAlert) -> str:
    payload = alert.payload or {}
    try:
        import os
        from openai import OpenAI
        if os.environ.get("AI_API_KEY"):
            client = OpenAI(api_key=os.environ["AI_API_KEY"], base_url="https://openrouter.ai/api/v1")
            result = client.chat.completions.create(model="anthropic/claude-sonnet-4", messages=[{"role": "system", "content": "Explain this alert in exactly two short sentences, plain English, with no math jargon or guarantees."}, {"role": "user", "content": f"{alert.message}\n{payload}"}], max_tokens=100)
            if result.choices[0].message.content:
                return result.choices[0].message.content.strip()
    except Exception:
        pass
    return f"This play favors {payload.get('selection', 'the highlighted outcome')} because the model sees more value than the current market price. It is not guaranteed, so execution still requires a fresh price, liquidity, and risk check."


@router.post("/telegram/webhook")
def telegram_webhook(update: dict, db: Session = Depends(get_db), telegram_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token")):
    if not telegram_secret_is_valid(telegram_secret):
        raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret.")
    settings = get_or_create_settings(db)
    callback = update.get("callback_query")
    if callback:
        message = callback.get("message") or {}
        chat_id = (message.get("chat") or {}).get("id")
        user_id = str((callback.get("from") or {}).get("id", ""))
        callback_parts = str(callback.get("data", "")).split(":")
        action = callback_parts[0] if callback_parts else ""
        raw_id = callback_parts[1] if len(callback_parts) > 1 else ""
        raw_amount = callback_parts[2] if len(callback_parts) > 2 else ""
        alert = db.query(SignalAlert).filter(SignalAlert.id == int(raw_id or 0)).first()
        if not alert or not chat_id:
            return {"ok": True}
        if action == "dismiss":
            _telegram_send(settings, chat_id, "Alert dismissed.")
        elif action == "explain":
            _telegram_send(settings, chat_id, _explain_alert(alert))
        elif not is_authorized_admin(settings, user_id):
            _telegram_send(settings, chat_id, "Trade actions are restricted to authorized admins.")
        else:
            payload = alert.payload or {}
            if action == "custom":
                create_trade_challenge(db, user_id, {"mode": "custom", "alert_id": alert.id})
                _telegram_send(settings, chat_id, "Reply with a dollar amount or share count. This request expires in 60 seconds.")
            else:
                create_trade_challenge(db, user_id, {"condition_id": payload.get("condition_id"), "token_id": payload.get("token_id"), "side": payload.get("side", "BUY"), "price": float(payload.get("price", payload.get("share_price", 0)) or 0) / (100 if float(payload.get("price", 0) or 0) > 1 else 1), "size": float(raw_amount or 0), "expected_value": payload.get("expected_value", payload.get("ev")), "confidence": payload.get("confidence")})
                _telegram_send(settings, chat_id, "🔒 Enter Security Passcode to authorize trade execution:")
        return {"ok": True}
    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    user_id = str((message.get("from") or {}).get("id", ""))
    text = str(message.get("text", "")).strip()
    if not chat_id or not text:
        return {"ok": True}
    challenge = db.query(TelegramAuthChallenge).filter(TelegramAuthChallenge.telegram_user_id == user_id, TelegramAuthChallenge.consumed_at.is_(None)).order_by(TelegramAuthChallenge.created_at.desc()).first()
    if challenge and challenge.expires_at > datetime.now(timezone.utc) and is_authorized_admin(settings, user_id):
        pending = challenge.pending_trade or {}
        if pending.get("mode") == "custom":
            import re
            match = re.search(r"\d+(?:\.\d+)?", text)
            if not match:
                _telegram_send(settings, chat_id, "Please send a valid dollar amount or share count.")
                return {"ok": True}
            alert = db.query(SignalAlert).filter(SignalAlert.id == pending["alert_id"]).first()
            payload = alert.payload if alert else {}
            price = float(payload.get("price", payload.get("share_price", 0)) or 0) / (100 if float(payload.get("price", 0) or 0) > 1 else 1)
            amount = float(match.group(0))
            size = amount / price if "$" in text and price > 0 else amount
            pending = {"condition_id": payload.get("condition_id"), "token_id": payload.get("token_id"), "side": payload.get("side", "BUY"), "price": price, "size": size, "expected_value": payload.get("expected_value", payload.get("ev")), "confidence": payload.get("confidence")}
            challenge.pending_trade = pending
            db.commit()
            _telegram_send(settings, chat_id, "🔒 Enter Security Passcode to authorize trade execution:")
            return {"ok": True}
        verified = verify_trade_challenge(db, settings, user_id, text)
        if verified:
            try:
                trade = _execute_trade(db, settings, TradeExecutionRequest(**verified, admin_telegram_id=user_id, security_pin=text))
                _telegram_send(settings, chat_id, f"Trade {trade.status}: {trade.size:g} shares at {(trade.executed_price or trade.requested_price):.3f}." if trade.status not in {"cancelled", "failed"} else "Trade canceled: Odds shifted or market liquidity is too low.")
            except HTTPException as exc:
                _telegram_send(settings, chat_id, str(exc.detail))
            return {"ok": True}
        _telegram_send(settings, chat_id, "Incorrect or expired passcode. No order was sent.")
        return {"ok": True}
    if text.startswith("/buy") and not is_authorized_admin(settings, user_id):
        _telegram_send(settings, chat_id, "Trade commands are restricted to authorized admins.")
    elif text.startswith("/buy"):
        import re
        match = re.search(r"\d+(?:\.\d+)?", text)
        alert = db.query(SignalAlert).order_by(SignalAlert.created_at.desc()).first()
        if not match or not alert:
            _telegram_send(settings, chat_id, "Use a Buy button on an alert or send /buy followed by an amount.")
        else:
            payload = alert.payload or {}
            price = float(payload.get("price", payload.get("share_price", 0)) or 0) / (100 if float(payload.get("price", 0) or 0) > 1 else 1)
            amount = float(match.group(0))
            create_trade_challenge(db, user_id, {"condition_id": payload.get("condition_id"), "token_id": payload.get("token_id"), "side": payload.get("side", "BUY"), "price": price, "size": amount / price if "$" in text and price > 0 else amount, "expected_value": payload.get("expected_value", payload.get("ev")), "confidence": payload.get("confidence")})
            _telegram_send(settings, chat_id, "🔒 Enter Security Passcode to authorize trade execution:")
    elif text.startswith("/topbets") or text.startswith("/predict") or "odds" in text.lower():
        alerts = db.query(SignalAlert).order_by(SignalAlert.created_at.desc()).limit(5).all()
        _telegram_send(settings, chat_id, "Top opportunities:\n" + "\n".join(f"• {_alert_text(alert).splitlines()[0]}" for alert in alerts) if alerts else "No current opportunities are available.")
    else:
        _telegram_send(settings, chat_id, "I can answer market questions and show current opportunities. Try /predict or /topbets.")
    return {"ok": True}
