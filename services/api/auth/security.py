from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from core.config import settings

# argon2, not bcrypt: passlib (unmaintained since 2020) has a known incompatibility with
# current bcrypt releases (it probes for a `bcrypt.__about__.__version__` attribute that no
# longer exists), so `passlib[bcrypt]` breaks on a fresh install. Argon2 sidesteps this
# entirely and is the better modern default regardless.
_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def create_access_token(*, sub: str, email: str, name: str, role: str, bank_id: str | None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_minutes)
    payload: dict[str, Any] = {
        "sub": sub,
        "email": email,
        "name": name,
        "role": role,
        "bank_id": bank_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
