"""Validates the bearer token the main platform (services/api) issued at
customer login, so a chat session can be tied to a real customer account
without agent-backend running its own login of its own.

Deliberately optional: a request with no Authorization header still starts
an anonymous chat session (this keeps the existing terminal test scripts in
scripts/ working unmodified). When a token IS present it must be valid and
must belong to a customer account — the customer-facing chat UI (built in
a later step) always sends one, so in practice every session started from
the product is tied to a real user from the moment it starts.
"""

from fastapi import HTTPException
from jose import JWTError, jwt

from app.core.config import get_settings


def get_customer_id_from_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None

    token = authorization.split(" ", 1)[1].strip()
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("role") != "customer":
        raise HTTPException(status_code=403, detail="Only customer accounts can use the loan chat assistant")

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=401, detail="Invalid token")
    return subject
