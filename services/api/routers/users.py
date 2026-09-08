import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import require_role
from core.database import get_db
from models.customer_profile import CustomerProfile
from models.enums import UserRole
from schemas.auth import UserClaims
from schemas.customer_profile import CustomerProfileOut, CustomerProfileUpdate

router = APIRouter(prefix="/users", tags=["users"])


async def _get_or_create_profile(db: AsyncSession, user_id: uuid.UUID) -> CustomerProfile:
    result = await db.execute(select(CustomerProfile).where(CustomerProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = CustomerProfile(user_id=user_id)
        db.add(profile)
        await db.flush()
    return profile


@router.get("/me/profile", response_model=CustomerProfileOut)
async def get_my_profile(
    user: UserClaims = Depends(require_role(UserRole.customer)),
    db: AsyncSession = Depends(get_db),
) -> CustomerProfileOut:
    profile = await _get_or_create_profile(db, uuid.UUID(user.sub))
    await db.commit()
    return CustomerProfileOut.model_validate(profile)


@router.patch("/me/profile", response_model=CustomerProfileOut)
async def update_my_profile(
    body: CustomerProfileUpdate,
    user: UserClaims = Depends(require_role(UserRole.customer)),
    db: AsyncSession = Depends(get_db),
) -> CustomerProfileOut:
    profile = await _get_or_create_profile(db, uuid.UUID(user.sub))
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.commit()
    return CustomerProfileOut.model_validate(profile)
