from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import InstitutionalSettings, TelegramAuthChallenge

RISK_PRESETS: dict[str, dict[str, float]] = {
    "conservative": {"confidence": 0.82, "minimum_liquidity": 500.0, "max_trade_multiplier": 0.5},
    "balanced": {"confidence": 0.75, "minimum_liquidity": 250.0, "max_trade_multiplier": 1.0},
    "aggressive": {"confidence": 0.75, "minimum_liquidity": 100.0, "max_trade_multiplier": 2.0},
}


def get_or_create_settings(db: Session) -> InstitutionalSettings:
    settings = db.query(InstitutionalSettings).order_by(InstitutionalSettings.id.asc()).first()
    if settings is None:
        settings = InstitutionalSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def public_settings(settings: InstitutionalSettings) -> dict[str, Any]:
    return {
        "id": settings.id,
        "organization_name": settings.organization_name,
        "execution_mode": settings.execution_mode,
        "risk_preset": settings.risk_preset,
        "max_trade_amount": settings.max_trade_amount,
        "authorized_admin_telegram_ids": settings.authorized_admin_telegram_ids or [],
        "has_telegram_bot_token": bool(settings.telegram_bot_token),
        "has_polymarket_credentials": all(
            [settings.polymarket_api_key, settings.polymarket_api_secret, settings.polymarket_passphrase]
        ),
        "has_wallet_private_key": bool(settings.wallet_private_key),
        "has_admin_security_pin": bool(settings.admin_security_pin),
        "updated_at": settings.updated_at,
    }


def is_authorized_admin(settings: InstitutionalSettings, telegram_user_id: str | int | None) -> bool:
    if telegram_user_id is None:
        return False
    return str(telegram_user_id) in {str(value) for value in (settings.authorized_admin_telegram_ids or [])}


def validate_risk_preset(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in RISK_PRESETS:
        raise HTTPException(status_code=422, detail="Risk preset must be conservative, balanced, or aggressive.")
    return normalized


def guardrail_decision(
    settings: InstitutionalSettings,
    *,
    expected_value: float | None,
    confidence: float | None,
    liquidity: float,
    requested_size: float,
    price_shift: float | None = None,
) -> dict[str, Any]:
    preset = RISK_PRESETS.get(settings.risk_preset, RISK_PRESETS["balanced"])
    ev = float(expected_value or 0.0)
    conf = float(confidence or 0.0)
    minimum_liquidity = float(preset["minimum_liquidity"])
    reasons: list[str] = []
    if ev <= 0.03:
        reasons.append("Expected value must be greater than 3.0%.")
    if conf < preset["confidence"]:
        reasons.append(f"Model confidence must be at least {preset['confidence']:.0%}.")
    if liquidity < minimum_liquidity or liquidity < requested_size:
        reasons.append("Available CLOB liquidity cannot support the requested size.")
    if price_shift is not None and abs(price_shift) > 0.02:
        reasons.append("Market price shifted beyond the permitted pre-execution tolerance.")
    max_size = settings.max_trade_amount * preset["max_trade_multiplier"]
    if requested_size > max_size:
        reasons.append("Requested size exceeds the active risk preset limit.")
    return {
        "passed": not reasons,
        "expected_value": ev,
        "confidence": conf,
        "liquidity": float(liquidity),
        "minimum_liquidity": minimum_liquidity,
        "reasons": reasons,
    }


def create_trade_challenge(db: Session, telegram_user_id: str, pending_trade: dict[str, Any]) -> TelegramAuthChallenge:
    raw = secrets.token_urlsafe(32)
    challenge = TelegramAuthChallenge(
        telegram_user_id=str(telegram_user_id),
        challenge_hash=hashlib.sha256(raw.encode()).hexdigest(),
        pending_trade=pending_trade,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=60),
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    return challenge


def verify_trade_challenge(db: Session, settings: InstitutionalSettings, telegram_user_id: str, pin: str) -> dict[str, Any] | None:
    challenge = (
        db.query(TelegramAuthChallenge)
        .filter(
            TelegramAuthChallenge.telegram_user_id == str(telegram_user_id),
            TelegramAuthChallenge.purpose == "trade",
            TelegramAuthChallenge.consumed_at.is_(None),
        )
        .order_by(TelegramAuthChallenge.created_at.desc())
        .first()
    )
    now = datetime.now(timezone.utc)
    if challenge is None or challenge.expires_at <= now:
        return None
    challenge.attempts += 1
    if challenge.attempts > 5 or not settings.admin_security_pin:
        db.commit()
        return None
    if not hmac.compare_digest(str(pin), str(settings.admin_security_pin)):
        db.commit()
        return None
    challenge.consumed_at = now
    db.commit()
    return challenge.pending_trade


def telegram_secret_is_valid(secret: str | None) -> bool:
    configured = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    return not configured or hmac.compare_digest(secret or "", configured)
