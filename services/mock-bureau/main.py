"""Mock credit bureau sandbox.

Mimics the OAuth2 client-credentials + Bearer-auth shape of a real credit bureau sandbox
API, so calling code can be pointed at a live provider later without changing its interface
— only the base URL and credentials change. Tokens are opaque, in-memory, and fake; nothing
here is a real credential or a real credit file. See `data/identities.py` for the synthetic
test identities.
"""

import secrets
import time

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from core.config import settings
from data.identities import find_identity, report_payload

app = FastAPI(title="Mock Credit Bureau Sandbox")

TOKEN_TTL_SECONDS = 3600

# In-memory opaque token store: token -> expiry (epoch seconds). Fine for a dev sandbox
# that's expected to be restarted freely; a real bureau would issue signed/verifiable tokens.
_issued_tokens: dict[str, float] = {}


class TokenRequest(BaseModel):
    client_id: str
    client_secret: str
    grant_type: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = TOKEN_TTL_SECONDS


class CreditReportRequest(BaseModel):
    name: str
    dob: str
    address: str


@app.post("/oauth2/v1/token", response_model=TokenResponse)
async def issue_token(body: TokenRequest) -> TokenResponse:
    if body.grant_type != "client_credentials":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")
    if (
        body.client_id != settings.mock_bureau_client_id
        or body.client_secret != settings.mock_bureau_client_secret
    ):
        raise HTTPException(status_code=401, detail="invalid_client")

    token = secrets.token_urlsafe(32)
    _issued_tokens[token] = time.time() + TOKEN_TTL_SECONDS
    return TokenResponse(access_token=token)


def _require_valid_token(authorization: str | None) -> None:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing_bearer_token")
    token = authorization.removeprefix("Bearer ").strip()
    expiry = _issued_tokens.get(token)
    if expiry is None or expiry < time.time():
        raise HTTPException(status_code=401, detail="invalid_or_expired_token")


@app.post("/credit-report/v1")
async def credit_report(
    body: CreditReportRequest, authorization: str | None = Header(default=None)
) -> dict:
    _require_valid_token(authorization)

    identity = find_identity(body.name, body.dob, body.address)
    if identity is None:
        return {"matched": False}
    return report_payload(identity)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
