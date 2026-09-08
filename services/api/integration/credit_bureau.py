from typing import Any

import httpx
from pydantic import BaseModel

from core.config import settings


class CreditBureauResult(BaseModel):
    """`called` is always True for a result returned by `get_credit_report` (callers only
    invoke it when they intend to call out); `matched`/`error` distinguish a legitimate
    no-match from a failed call. Never carries a synthesised score — `score`/`band` are
    only ever populated from a bureau response with `matched: True`."""

    called: bool = True
    matched: bool | None = None
    score: int | None = None
    band: str | None = None
    report_summary: dict[str, Any] | None = None
    error: str | None = None


async def _get_access_token(client: httpx.AsyncClient) -> str:
    """Raises on failure (caller distinguishes timeout / auth failure / other transport
    errors) rather than swallowing the error here, so `get_credit_report` can report an
    accurate `error` reason instead of a single generic failure."""
    response = await client.post(
        "/oauth2/v1/token",
        json={
            "client_id": settings.mock_bureau_client_id,
            "client_secret": settings.mock_bureau_client_secret,
            "grant_type": "client_credentials",
        },
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not isinstance(token, str):
        raise ValueError("access_token missing from token response")
    return token


async def get_credit_report(
    name: str, dob: str, address: str, *, client: httpx.AsyncClient | None = None
) -> CreditBureauResult:
    """Calls the credit bureau (mock sandbox by default, per settings.mock_bureau_base_url)
    to look up `name`/`dob`/`address`. Never raises — a timeout, connection failure, auth
    failure or malformed response all degrade to `CreditBureauResult(error=...)` so the
    caller can mark Character `unavailable` rather than the whole assessment failing.

    `client` is an injection seam for tests (an `httpx.AsyncClient` built on
    `httpx.MockTransport`) — production callers should omit it."""
    owns_client = client is None
    http_client = client or httpx.AsyncClient(
        base_url=settings.mock_bureau_base_url, timeout=settings.mock_bureau_timeout_seconds
    )
    try:
        try:
            token = await _get_access_token(http_client)
        except httpx.HTTPStatusError:
            return CreditBureauResult(matched=None, error="auth_failed")

        response = await http_client.post(
            "/credit-report/v1",
            json={"name": name, "dob": dob, "address": address},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException:
        return CreditBureauResult(matched=None, error="timeout")
    except httpx.HTTPError:
        return CreditBureauResult(matched=None, error="request_failed")
    except ValueError:
        return CreditBureauResult(matched=None, error="malformed_response")
    finally:
        if owns_client:
            await http_client.aclose()

    if not data.get("matched"):
        return CreditBureauResult(matched=False)

    return CreditBureauResult(
        matched=True,
        score=data.get("score"),
        band=data.get("band"),
        report_summary=data.get("report_summary"),
    )
