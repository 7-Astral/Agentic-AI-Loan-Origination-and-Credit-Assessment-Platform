import json
import re

import httpx
from pydantic import BaseModel

from core.config import settings

ABR_BASE_URL = "https://abr.business.gov.au/json/AbnDetails.aspx"

# The endpoint returns JSONP: `callback({...})`. This unwraps whatever function name is
# used (we always pass `callback=callback`, but the regex isn't tied to that literal).
_JSONP_RE = re.compile(r"^\s*[A-Za-z0-9_]+\((.*)\)\s*;?\s*$", re.DOTALL)


class AbrResult(BaseModel):
    """`found` is None when the lookup itself couldn't be made (no GUID configured, timeout,
    network failure) — the caller should treat that as `unavailable`, distinct from `found:
    False`, a definitive "no such ABN" answer from the ABR."""

    called: bool = True
    found: bool | None = None
    entity_name: str | None = None
    abn_status: str | None = None
    entity_type: str | None = None
    gst_registered: bool | None = None
    address_state: str | None = None
    error: str | None = None


def _strip_jsonp(text: str) -> dict:
    match = _JSONP_RE.match(text)
    body = match.group(1) if match else text
    return json.loads(body)


def _is_invalid_or_unknown(payload: dict) -> bool:
    """The ABR endpoint responds 200 for an invalid/unknown ABN too, with an `Exception`
    message (bad format) or no `Abn` field (no matching record) in the payload instead of
    an HTTP error — so the payload has to be inspected rather than trusting the status."""
    if payload.get("Exception"):
        return True
    return not payload.get("Abn")


async def lookup_abn(abn: str, *, client: httpx.AsyncClient | None = None) -> AbrResult:
    """Looks up `abn` against the ABR web service. Never raises: a missing ABR_GUID, a
    timeout, a network failure or a malformed response all degrade to
    `AbrResult(found=None, error=...)` so the caller can mark Conditions' ABN details
    `unavailable` rather than failing the whole assessment.

    `client` is an injection seam for tests (an `httpx.AsyncClient` built on
    `httpx.MockTransport`) — production callers should omit it."""
    if not settings.abr_guid:
        return AbrResult(found=None, error="no_guid")

    owns_client = client is None
    http_client = client or httpx.AsyncClient(timeout=settings.abr_timeout_seconds)
    try:
        response = await http_client.get(
            ABR_BASE_URL,
            params={"abn": abn.replace(" ", ""), "guid": settings.abr_guid, "callback": "callback"},
        )
        response.raise_for_status()
        payload = _strip_jsonp(response.text)
    except httpx.TimeoutException:
        return AbrResult(found=None, error="timeout")
    except httpx.HTTPError:
        return AbrResult(found=None, error="request_failed")
    except (json.JSONDecodeError, ValueError):
        return AbrResult(found=None, error="malformed_response")
    finally:
        if owns_client:
            await http_client.aclose()

    if _is_invalid_or_unknown(payload):
        return AbrResult(found=False)

    gst_raw = payload.get("Gst")

    return AbrResult(
        found=True,
        entity_name=payload.get("EntityName") or None,
        abn_status=payload.get("AbnStatus") or None,
        entity_type=payload.get("EntityTypeName") or None,
        gst_registered=bool(gst_raw) if gst_raw is not None else None,
        address_state=payload.get("AddressState") or None,
    )
