from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

try:
    from py_clob_client import ApiCreds, ClobClient, OrderArgs
    from py_clob_client.order_builder.constants import BUY, SELL
except ImportError:  # pragma: no cover - deployment without optional trading package
    ApiCreds = None
    ClobClient = None
    OrderArgs = None
    BUY = "BUY"
    SELL = "SELL"

CLOB_HOST = "https://clob.polymarket.com"
POLYGON_CHAIN_ID = 137


def _numeric(value: Any) -> float:
    if isinstance(value, dict):
        value = value.get("price") or value.get("size") or 0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def order_book_liquidity(book: Any, side: str = "BUY") -> float:
    levels = getattr(book, "asks" if side.upper() == "BUY" else "bids", None)
    if levels is None and isinstance(book, dict):
        levels = book.get("asks" if side.upper() == "BUY" else "bids", [])
    total = 0.0
    for level in levels or []:
        if isinstance(level, dict):
            total += _numeric(level.get("size"))
        else:
            total += _numeric(getattr(level, "size", 0))
    return total


def build_client(settings: Any) -> Any:
    if ClobClient is None or ApiCreds is None:
        raise HTTPException(status_code=503, detail="Polymarket execution is not available in this deployment.")
    required = [
        settings.wallet_private_key,
        settings.polymarket_api_key,
        settings.polymarket_api_secret,
        settings.polymarket_passphrase,
    ]
    if not all(required):
        raise HTTPException(status_code=503, detail="Polymarket credentials are not configured.")
    client = ClobClient(
        CLOB_HOST,
        chain_id=POLYGON_CHAIN_ID,
        key=settings.wallet_private_key,
    )
    client.set_api_creds(
        ApiCreds(
            api_key=settings.polymarket_api_key,
            api_secret=settings.polymarket_api_secret,
            api_passphrase=settings.polymarket_passphrase,
        )
    )
    return client


def read_live_market(settings: Any, token_id: str, side: str, requested_size: float) -> dict[str, float]:
    client = build_client(settings)
    normalized_side = side.upper()
    live_price = _numeric(client.get_price(token_id, normalized_side))
    book = client.get_order_book(token_id)
    liquidity = order_book_liquidity(book, normalized_side)
    return {"price": live_price, "liquidity": liquidity, "requested_size": requested_size}


def submit_limit_order(settings: Any, token_id: str, side: str, price: float, size: float) -> dict[str, Any]:
    client = build_client(settings)
    normalized_side = BUY if side.upper() == "BUY" else SELL
    order = client.create_order(OrderArgs(token_id=token_id, price=price, size=size, side=normalized_side))
    response = client.post_order(order)
    if isinstance(response, dict):
        order_id = response.get("orderID") or response.get("order_id") or response.get("id")
    else:
        order_id = getattr(response, "orderID", None) or getattr(response, "order_id", None)
    return {
        "order_id": str(order_id) if order_id else None,
        "response": response if isinstance(response, dict) else {"result": str(response)},
        "executed_at": datetime.now(timezone.utc),
    }
