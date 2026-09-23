"""Gateway configuration (Appifex scaffold).

Loads GATEWAY_URL and APPIFEX_GATEWAY_API_KEY from environment.
Both are auto-injected at deployment — do not hardcode.
"""

import os

from fastapi import HTTPException

GATEWAY_URL = os.environ.get(
    "GATEWAY_URL", "https://appifex-gateway.appifex-ai.workers.dev"
)
GATEWAY_API_KEY = os.environ.get("APPIFEX_GATEWAY_API_KEY", "")


def validate_config():
    if not GATEWAY_URL or not GATEWAY_API_KEY:
        missing = []
        if not GATEWAY_URL:
            missing.append("GATEWAY_URL")
        if not GATEWAY_API_KEY:
            missing.append("APPIFEX_GATEWAY_API_KEY")
        raise HTTPException(
            status_code=500,
            detail=f"Gateway configuration missing: {', '.join(missing)}",
        )


def get_api_key():
    api_key = os.environ.get("APPIFEX_GATEWAY_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="Gateway API key not configured")
    return api_key
