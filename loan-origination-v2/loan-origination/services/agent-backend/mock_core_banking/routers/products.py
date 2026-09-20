from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mock_core_banking.db import get_session
from mock_core_banking.models import Category, Product
from mock_core_banking.routers.deps import get_bank_or_404
from mock_core_banking.schemas import ProductCreate, ProductOut, ProductUpdate

router = APIRouter(prefix="/api/v1/banks/{bank_id}/products", tags=["admin:products"])


async def _validate_category(session: AsyncSession, bank_id: str, loan_type_code: str, category_code: str) -> None:
    result = await session.execute(
        select(Category).where(
            Category.bank_id == bank_id,
            Category.loan_type_code == loan_type_code,
            Category.code == category_code,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            400, f"'{category_code}' is not a valid category for loan_type '{loan_type_code}' on this bank"
        )


@router.get("", response_model=list[ProductOut])
async def list_products(bank_id: str, session: AsyncSession = Depends(get_session)):
    await get_bank_or_404(bank_id, session)
    result = await session.execute(select(Product).where(Product.bank_id == bank_id))
    return list(result.scalars().all())


@router.post("", response_model=ProductOut, status_code=201)
async def create_product(
    bank_id: str, payload: ProductCreate, session: AsyncSession = Depends(get_session)
):
    await get_bank_or_404(bank_id, session)
    await _validate_category(session, bank_id, payload.loan_type_code, payload.category_code)

    existing = await session.get(Product, {"bank_id": bank_id, "product_code": payload.product_code})
    if existing is not None:
        raise HTTPException(409, f"Product '{payload.product_code}' already exists for this bank")

    product = Product(bank_id=bank_id, **payload.model_dump())
    session.add(product)
    await session.commit()
    return product


@router.put("/{product_code}", response_model=ProductOut)
async def update_product(
    bank_id: str,
    product_code: str,
    payload: ProductUpdate,
    session: AsyncSession = Depends(get_session),
):
    await get_bank_or_404(bank_id, session)
    product = await session.get(Product, {"bank_id": bank_id, "product_code": product_code})
    if product is None:
        raise HTTPException(404, f"Product '{product_code}' not found for this bank")
    await _validate_category(session, bank_id, payload.loan_type_code, payload.category_code)

    for field, value in payload.model_dump().items():
        setattr(product, field, value)
    product.product_code = product_code

    await session.commit()
    return product


@router.delete("/{product_code}", status_code=204)
async def delete_product(
    bank_id: str, product_code: str, session: AsyncSession = Depends(get_session)
):
    await get_bank_or_404(bank_id, session)
    product = await session.get(Product, {"bank_id": bank_id, "product_code": product_code})
    if product is None:
        raise HTTPException(404, f"Product '{product_code}' not found for this bank")
    await session.delete(product)
    await session.commit()
