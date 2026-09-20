import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def get_credit_report(filled: dict[str, Any], scenario: str | None = None) -> dict | None:
    if not filled.get("credit_check_consent"):
        return None
    full_name = filled.get("full_name")
    date_of_birth = filled.get("date_of_birth")
    if not full_name or not date_of_birth:
        return None

    s = get_settings()
    payload = {
        "full_name": full_name,
        "date_of_birth": date_of_birth,
        "current_address": filled.get("current_address"),
        "consent": True,
        "scenario": scenario or s.bureau_mock_scenario or None,
    }
    try:
        async with httpx.AsyncClient(timeout=s.bureau_timeout) as client:
            resp = await client.post(
                f"{s.bureau_base_url.rstrip('/')}/api/v1/credit-report",
                json=payload, headers={"X-API-Key": s.bureau_api_key},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        logger.warning("Credit bureau request failed (%s); character metrics will be unavailable", repr(exc))
        return None


async def list_scenarios() -> list[dict]:
    s = get_settings()
    try:
        async with httpx.AsyncClient(timeout=s.bureau_timeout) as client:
            resp = await client.get(f"{s.bureau_base_url.rstrip('/')}/api/v1/scenarios")
            resp.raise_for_status()
            return resp.json()["scenarios"]
    except httpx.HTTPError as exc:
        logger.warning("Could not list bureau scenarios (%s)", repr(exc))
        return []
