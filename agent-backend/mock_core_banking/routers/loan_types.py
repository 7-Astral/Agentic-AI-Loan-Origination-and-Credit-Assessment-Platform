from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mock_core_banking.db import get_session
from mock_core_banking.models import Category, LoanType
from mock_core_banking.routers.deps import get_bank_or_404
from mock_core_banking.schemas import (
    CategoryCreate,
    CategoryOut,
    CategoryRename,
    LoanTypeCreate,
    LoanTypeOut,
    LoanTypeUpdate,
)

router = APIRouter(prefix="/api/v1/banks/{bank_id}/loan-types", tags=["admin:loan-types"])


async def _loan_type_out(session: AsyncSession, bank_id: str, loan_type: LoanType) -> LoanTypeOut:
    cats = await session.execute(
        select(Category).where(Category.bank_id == bank_id, Category.loan_type_code == loan_type.code)
    )
    categories = [CategoryOut(code=c.code, name=c.name) for c in cats.scalars().all()]
    return LoanTypeOut(
        code=loan_type.code, name=loan_type.name, description=loan_type.description,
        categories=categories,
    )


async def _get_loan_type_or_404(session: AsyncSession, bank_id: str, code: str) -> LoanType:
    lt = await session.get(LoanType, {"bank_id": bank_id, "code": code})
    if lt is None:
        raise HTTPException(404, f"Loan type '{code}' not found for bank '{bank_id}'")
    return lt


@router.get("", response_model=list[LoanTypeOut])
async def list_loan_types(bank_id: str, session: AsyncSession = Depends(get_session)):
    await get_bank_or_404(bank_id, session)
    result = await session.execute(select(LoanType).where(LoanType.bank_id == bank_id))
    return [await _loan_type_out(session, bank_id, lt) for lt in result.scalars().all()]


@router.post("", response_model=LoanTypeOut, status_code=201)
async def create_loan_type(
    bank_id: str, payload: LoanTypeCreate, session: AsyncSession = Depends(get_session)
):
    await get_bank_or_404(bank_id, session)
    existing = await session.get(LoanType, {"bank_id": bank_id, "code": payload.code})
    if existing is not None:
        raise HTTPException(409, f"Loan type '{payload.code}' already exists for this bank")
    lt = LoanType(bank_id=bank_id, code=payload.code, name=payload.name, description=payload.description)
    session.add(lt)
    await session.commit()
    return await _loan_type_out(session, bank_id, lt)


@router.patch("/{code}", response_model=LoanTypeOut)
async def update_loan_type(
    bank_id: str, code: str, payload: LoanTypeUpdate, session: AsyncSession = Depends(get_session)
):
    await get_bank_or_404(bank_id, session)
    lt = await _get_loan_type_or_404(session, bank_id, code)
    lt.name = payload.name
    lt.description = payload.description
    await session.commit()
    return await _loan_type_out(session, bank_id, lt)


@router.post("/{code}/categories", response_model=CategoryOut, status_code=201)
async def add_category(
    bank_id: str, code: str, payload: CategoryCreate, session: AsyncSession = Depends(get_session)
):
    await get_bank_or_404(bank_id, session)
    await _get_loan_type_or_404(session, bank_id, code)

    existing = await session.execute(
        select(Category).where(
            Category.bank_id == bank_id, Category.loan_type_code == code, Category.code == payload.code
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(409, f"Category '{payload.code}' already exists under loan type '{code}'")

    category = Category(bank_id=bank_id, loan_type_code=code, code=payload.code, name=payload.name)
    session.add(category)
    await session.commit()
    return CategoryOut(code=category.code, name=category.name)


@router.patch("/{code}/categories/{category_code}", response_model=CategoryOut)
async def rename_category(
    bank_id: str,
    code: str,
    category_code: str,
    payload: CategoryRename,
    session: AsyncSession = Depends(get_session),
):
    await get_bank_or_404(bank_id, session)
    result = await session.execute(
        select(Category).where(
            Category.bank_id == bank_id, Category.loan_type_code == code, Category.code == category_code
        )
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(404, f"Category '{category_code}' not found under loan type '{code}'")
    category.name = payload.name
    await session.commit()
    return CategoryOut(code=category.code, name=category.name)
