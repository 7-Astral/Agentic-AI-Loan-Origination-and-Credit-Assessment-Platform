import uuid

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.bank_position import BankPosition
from app.models.enums import UserRole
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def require_service_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Guards server-to-server endpoints (e.g. the chat-agent backend reading
    the catalog or posting a completed application) with a shared secret,
    the same pattern agent-backend already uses for mock_core_banking."""
    if x_api_key != settings.service_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_role(*allowed_roles: str):
    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _check


async def get_current_staff(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.STAFF.value or not user.bank_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bank staff access required")
    return user


def require_bank_permission(permission: str):
    """Gate on a permission carried by the staff member's position (e.g.
    'can_manage_staff', 'can_manage_products') rather than a fixed role —
    the hierarchy and thresholds are configured per bank, not hardcoded."""

    async def _check(staff: User = Depends(get_current_staff), db: AsyncSession = Depends(get_db)) -> User:
        if not staff.position_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No position assigned")
        position = await db.get(BankPosition, staff.position_id)
        if not position or not getattr(position, permission, False):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient authority for this action")
        return staff

    return _check


async def require_bank_manager(staff: User = Depends(get_current_staff), db: AsyncSession = Depends(get_db)) -> User:
    """Stricter than require_bank_permission: requires a position with BOTH
    can_manage_staff and can_manage_products — i.e. an actual bank manager
    (the "Branch Manager" position create_bank auto-creates), not just
    someone with one partial permission. Used for things a manager alone
    should see, like the bank's own audit log."""
    if not staff.position_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No position assigned")
    position = await db.get(BankPosition, staff.position_id)
    if not position or not (position.can_manage_staff and position.can_manage_products):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager authority required for this action")
    return staff
