from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.bank import Bank
from models.enums import BankStatus
from models.loan_product import LoanProduct
from schemas.bank import BankOut, LoanProductOut

router = APIRouter(prefix="/banks", tags=["banks"])


@router.get("/{slug}", response_model=BankOut)
async def get_bank(slug: str, db: AsyncSession = Depends(get_db)) -> BankOut:
    stmt = select(Bank).where(Bank.slug == slug, Bank.status == BankStatus.active)
    result = await db.execute(stmt)
    bank = result.scalar_one_or_none()
    if bank is None:
        raise HTTPException(status_code=404, detail="Bank not found")

    products_stmt = select(LoanProduct).where(
        LoanProduct.bank_id == bank.id, LoanProduct.active.is_(True)
    )
    products_result = await db.execute(products_stmt)
    products = [LoanProductOut.model_validate(p) for p in products_result.scalars().all()]

    return BankOut(
        id=bank.id, name=bank.name, slug=bank.slug, branding=bank.branding, products=products
    )
