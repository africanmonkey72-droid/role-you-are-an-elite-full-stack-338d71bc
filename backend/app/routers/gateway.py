"""Gateway proxy router (Appifex scaffold).

Routes weather and stock API calls through the Appifex Gateway.
DO NOT modify this file — it is managed by the scaffold service.

NOTE: AI/LLM capabilities (chat, vision, image gen, TTS, STT) are NOT here.
      Use backend OpenAI SDK calls guided by the ai-integration capability.
"""

import httpx
from app.gateway_config import GATEWAY_URL, get_api_key, validate_config
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/gateway", tags=["gateway"])


# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------


@router.get("/weather")
def get_weather(city: str, units: str = "metric"):
    validate_config()
    with httpx.Client(timeout=10.0) as client:
        response = client.get(
            f"{GATEWAY_URL}/weather/weather",
            params={"q": city, "units": units},
            headers={"x-appifex-key": get_api_key()},
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()


@router.get("/weather/forecast")
def get_weather_forecast(city: str, units: str = "metric", days: int = 5):
    validate_config()
    with httpx.Client(timeout=10.0) as client:
        response = client.get(
            f"{GATEWAY_URL}/weather/forecast",
            params={"q": city, "units": units, "cnt": days},
            headers={"x-appifex-key": get_api_key()},
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()


# ---------------------------------------------------------------------------
# Stocks
# ---------------------------------------------------------------------------


@router.get("/stocks/quote")
def get_stock_quote(symbol: str):
    validate_config()
    with httpx.Client(timeout=10.0) as client:
        response = client.get(
            f"{GATEWAY_URL}/stocks/query",
            params={"function": "GLOBAL_QUOTE", "symbol": symbol.upper()},
            headers={"x-appifex-key": get_api_key()},
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()


@router.get("/stocks/search")
def search_stocks(keywords: str):
    validate_config()
    with httpx.Client(timeout=10.0) as client:
        response = client.get(
            f"{GATEWAY_URL}/stocks/query",
            params={"function": "SYMBOL_SEARCH", "keywords": keywords},
            headers={"x-appifex-key": get_api_key()},
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()
