from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from auth.factory import get_auth_provider
from auth.security import create_access_token, hash_password
from core.database import get_db
from models.enums import UserRole
from models.user import User
from schemas.auth import (
    AuthenticatedUser,
    Credentials,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserClaims,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_token(user: AuthenticatedUser) -> str:
    return create_access_token(
        sub=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role.value,
        bank_id=str(user.bank_id) if user.bank_id else None,
    )


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    provider = get_auth_provider(db)
    user = await provider.authenticate(Credentials(email=body.email, password=body.password))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    db_user = await db.get(User, user.id)
    if db_user is not None:
        db_user.last_login_at = datetime.now(UTC)
        await db.commit()

    return LoginResponse(access_token=_issue_token(user), user=user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout() -> None:
    """Client-side token discard is sufficient at this stage — this endpoint exists for
    symmetry and future token revocation once that's needed."""
    return None


@router.get("/me", response_model=AuthenticatedUser)
async def me(user: UserClaims = Depends(get_current_user)) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=user.sub, email=user.email, name=user.name, role=user.role, bank_id=user.bank_id
    )


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    """Customer self-registration only. `RegisterRequest` has no `role` field at all (see
    its docstring) — this handler additionally hardcodes UserRole.customer regardless, so
    there is no path by which a client can register as loan_officer/credit_manager/admin."""
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        bank_id=body.bank_id,
        name=body.name,
        email=body.email,
        role=UserRole.customer,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    authenticated = AuthenticatedUser(
        id=user.id, email=user.email, name=user.name, role=user.role, bank_id=user.bank_id
    )
    return LoginResponse(access_token=_issue_token(authenticated), user=authenticated)
