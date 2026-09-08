import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.security import decode_access_token, verify_password
from models.enums import UserRole
from models.user import User
from schemas.auth import AuthenticatedUser, Credentials, UserClaims


async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


class LocalAuthProvider:
    """Local email/password auth — a documented dev-stage substitute for Entra ID / Azure
    AD B2C, selected via `AUTH_PROVIDER=local` (see auth/factory.py and CLAUDE.md)."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def authenticate(self, credentials: Credentials) -> AuthenticatedUser | None:
        user = await _get_user_by_email(self._db, credentials.email)
        if user is None or user.password_hash is None or not user.is_active:
            return None
        if not verify_password(credentials.password, user.password_hash):
            return None
        return AuthenticatedUser(
            id=user.id, email=user.email, name=user.name, role=user.role, bank_id=user.bank_id
        )

    async def get_user_claims(self, token: str) -> UserClaims | None:
        payload = decode_access_token(token)
        if payload is None:
            return None
        try:
            bank_id = payload.get("bank_id")
            return UserClaims(
                sub=payload["sub"],
                email=payload["email"],
                name=payload["name"],
                role=UserRole(payload["role"]),
                bank_id=uuid.UUID(bank_id) if bank_id else None,
            )
        except (KeyError, ValueError):
            return None
