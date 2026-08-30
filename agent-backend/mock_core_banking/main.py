from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .db import get_session
from .models import LoanType, Category, Product, DocumentType, DocumentRequirement
from .slots.registry import schema_for

app = FastAPI(title="Mock Core Banking API", version="0.1.0")


def product_to_dict(p: Product) -> dict:
    return {
        "product_code": p.product_code, "name": p.name,
        "loan_type": p.loan_type_code, "category": p.category_code,
        "secured": p.secured, "min_amount": p.min_amount, "max_amount": p.max_amount,
        "min_term_months": p.min_term_months, "max_term_months": p.max_term_months,
        "interest_rate": p.interest_rate, "comparison_rate": p.comparison_rate,
        "rate_type": p.rate_type, "establishment_fee": p.establishment_fee,
        "max_lvr": p.max_lvr, "features": p.features,
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "mock-core-banking"}


@app.get("/api/v1/loan-types")
async def list_loan_types(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(LoanType))
    loan_types = result.scalars().all()

    enriched = []
    for lt in loan_types:
        cat_result = await session.execute(
            select(Category.code, Category.name).where(Category.loan_type_code == lt.code)
        )
        categories = [{"code": row[0], "name": row[1]} for row in cat_result.all()]
        enriched.append({
            "code": lt.code, "name": lt.name, "description": lt.description,
            "categories": categories,
        })
    return {"loan_types": enriched}


@app.get("/api/v1/products")
async def list_products(
    loan_type: str | None = Query(default=None),
    category: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Product)
    if loan_type:
        stmt = stmt.where(Product.loan_type_code == loan_type)
    if category:
        stmt = stmt.where(Product.category_code == category)

    result = await session.execute(stmt)
    items = result.scalars().all()

    if not items:
        if loan_type and category:
            raise HTTPException(404, f"No products for category '{category}' under loan type '{loan_type}'")
        if loan_type:
            raise HTTPException(404, f"No products for loan type '{loan_type}'")
        if category:
            raise HTTPException(404, f"No products for category '{category}'")

    return {"count": len(items), "products": [product_to_dict(p) for p in items]}


@app.get("/api/v1/products/{product_code}")
async def get_product(product_code: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Product).where(Product.product_code.ilike(product_code))
    )
    p = result.scalar_one_or_none()
    if p is None:
        raise HTTPException(404, f"Product '{product_code}' not found")
    return product_to_dict(p)


@app.get("/api/v1/products/{product_code}/requirements")
async def get_product_requirements(product_code: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Product).where(Product.product_code.ilike(product_code))
    )
    p = result.scalar_one_or_none()
    if p is None:
        raise HTTPException(404, f"Product '{product_code}' not found")

    schema = schema_for(p.product_code)
    schema["loan_type"] = p.loan_type_code
    return schema


class ProductIn(BaseModel):
    product_code: str
    name: str
    loan_type: str
    category: str
    secured: bool = False
    min_amount: int
    max_amount: int
    min_term_months: int
    max_term_months: int
    interest_rate: float
    comparison_rate: float
    rate_type: str
    establishment_fee: int
    max_lvr: int | None = None
    features: list[str] = []


@app.post("/api/v1/products", status_code=201)
async def create_product(payload: ProductIn, session: AsyncSession = Depends(get_session)):
    lt = await session.get(LoanType, payload.loan_type)
    if lt is None:
        raise HTTPException(400, f"Unknown loan_type '{payload.loan_type}'")

    cat_result = await session.execute(
        select(Category).where(
            Category.loan_type_code == payload.loan_type,
            Category.code == payload.category,
        )
    )
    if cat_result.scalar_one_or_none() is None:
        raise HTTPException(
            400,
            f"'{payload.category}' is not a valid category for loan_type '{payload.loan_type}'"
        )

    existing = await session.get(Product, payload.product_code)
    if existing is not None:
        raise HTTPException(409, f"Product '{payload.product_code}' already exists")

    p = Product(
        product_code=payload.product_code, name=payload.name,
        loan_type_code=payload.loan_type, category_code=payload.category,
        secured=payload.secured, min_amount=payload.min_amount, max_amount=payload.max_amount,
        min_term_months=payload.min_term_months, max_term_months=payload.max_term_months,
        interest_rate=payload.interest_rate, comparison_rate=payload.comparison_rate,
        rate_type=payload.rate_type, establishment_fee=payload.establishment_fee,
        max_lvr=payload.max_lvr, features=payload.features,
    )
    session.add(p)
    await session.commit()
    return product_to_dict(p)


@app.get("/api/v1/loan-types/{loan_type}/categories/{category}/document-requirements")
async def get_document_requirements(
    loan_type: str, category: str, session: AsyncSession = Depends(get_session)
):
    stmt = (
        select(DocumentType.code, DocumentType.name)
        .join(DocumentRequirement, DocumentRequirement.document_type_code == DocumentType.code)
        .where(
            DocumentRequirement.loan_type_code == loan_type,
            DocumentRequirement.category_code == category,
        )
    )
    result = await session.execute(stmt)
    rows = result.all()
    if not rows:
        raise HTTPException(404, f"No document requirements found for {loan_type}/{category}")
    return {
        "loan_type": loan_type,
        "category": category,
        "documents": [{"code": r[0], "name": r[1]} for r in rows],
    }