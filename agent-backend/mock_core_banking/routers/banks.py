import re
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mock_core_banking.db import get_session
from mock_core_banking.models import Bank
from mock_core_banking.routers.deps import get_bank_or_404
from mock_core_banking.schemas import BankCreate, BankOut, BankUpdate

router = APIRouter(prefix="/api/v1/banks", tags=["banks"])


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "bank"
    return base


async def _unique_slug(session: AsyncSession, name: str) -> str:
    base = _slugify(name)
    slug = base
    suffix = 2
    while (await session.execute(select(Bank).where(Bank.slug == slug))).scalar_one_or_none():
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


@router.get("", response_model=list[BankOut])
async def list_banks(session: AsyncSession = Depends(get_session)) -> list[Bank]:
    result = await session.execute(select(Bank).order_by(Bank.created_at))
    return list(result.scalars().all())


@router.post("", response_model=BankOut, status_code=201)
async def create_bank(payload: BankCreate, session: AsyncSession = Depends(get_session)) -> Bank:
    bank = Bank(
        id=uuid.uuid4().hex[:12],
        name=payload.name,
        slug=await _unique_slug(session, payload.name),
        primary_color=payload.primary_color,
        status=payload.status,
    )
    session.add(bank)
    await session.commit()
    await session.refresh(bank)
    return bank


@router.get("/{bank_id}", response_model=BankOut)
async def get_bank(bank_id: str, session: AsyncSession = Depends(get_session)) -> Bank:
    return await get_bank_or_404(bank_id, session)


@router.patch("/{bank_id}", response_model=BankOut)
async def update_bank(
    bank_id: str, payload: BankUpdate, session: AsyncSession = Depends(get_session)
) -> Bank:
    bank = await get_bank_or_404(bank_id, session)
    bank.name = payload.name
    bank.primary_color = payload.primary_color
    bank.status = payload.status
    await session.commit()
    await session.refresh(bank)
    return bank
