"""Guards server-to-server endpoints called BY services/api (the main
platform), mirroring the shared-secret pattern services/api itself already
uses for calls going the other way (app.core.deps.require_service_api_key
there checks the same shared value).

Reuses the catalog_api_key setting: it's already the shared secret this
service sends as X-API-Key when it calls services/api's catalog, and
services/api's own default (SERVICE_API_KEY) is configured to match it —
one shared secret, checked on both sides.
"""

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


async def require_service_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if x_api_key != settings.catalog_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
