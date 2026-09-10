from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from mock_core_banking.models import Bank

DEFAULT_BANK_ID = "default"


async def get_bank_or_404(bank_id: str, session: AsyncSession) -> Bank:
    bank = await session.get(Bank, bank_id)
    if bank is None:
        raise HTTPException(404, f"Bank '{bank_id}' not found")
    return bank
