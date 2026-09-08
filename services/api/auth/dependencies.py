from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from auth.factory import get_auth_provider
from core.database import get_db
from models.enums import UserRole
from schemas.auth import UserClaims

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserClaims:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    provider = get_auth_provider(db)
    claims = await provider.get_user_claims(credentials.credentials)
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    return claims


def require_role(*roles: UserRole):
    """403s if the authenticated user's role isn't one of `roles`. Role checks alone are
    never sufficient — every route also enforces data ownership (customer_id / bank_id)
    separately; see routers/applications.py."""

    async def _check(user: UserClaims = Depends(get_current_user)) -> UserClaims:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return _check
