from fastapi import FastAPI, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.middleware.cors import CORSMiddleware

from .db import get_session
from .models import LoanType, Category, Product, DocumentType, DocumentRequirement, PolicySetting, Rule
from .routers.deps import DEFAULT_BANK_ID
from .routers import banks, documents, loan_types, policy, products, rules
from .slots.registry import schema_for

app = FastAPI(title="Mock Core Banking API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(banks.router)
app.include_router(loan_types.router)
app.include_router(products.router)
app.include_router(documents.router)
app.include_router(policy.router)
app.include_router(rules.router)

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
async def list_loan_types(
    bank_id: str = Query(default=DEFAULT_BANK_ID),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(LoanType).where(LoanType.bank_id == bank_id))
    loan_types = result.scalars().all()

    enriched = []
    for lt in loan_types:
        cat_result = await session.execute(
            select(Category.code, Category.name).where(
                Category.bank_id == bank_id, Category.loan_type_code == lt.code
            )
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
    bank_id: str = Query(default=DEFAULT_BANK_ID),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Product).where(Product.bank_id == bank_id)
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
async def get_product(
    product_code: str,
    bank_id: str = Query(default=DEFAULT_BANK_ID),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Product).where(Product.bank_id == bank_id, Product.product_code.ilike(product_code))
    )
    p = result.scalar_one_or_none()
    if p is None:
        raise HTTPException(404, f"Product '{product_code}' not found")
    return product_to_dict(p)


@app.get("/api/v1/products/{product_code}/requirements")
async def get_product_requirements(
    product_code: str,
    bank_id: str = Query(default=DEFAULT_BANK_ID),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Product).where(Product.bank_id == bank_id, Product.product_code.ilike(product_code))
    )
    p = result.scalar_one_or_none()
    if p is None:
        raise HTTPException(404, f"Product '{product_code}' not found")

    schema = schema_for(p.product_code)
    schema["loan_type"] = p.loan_type_code
    return schema


@app.get("/api/v1/interview-schema/{product_code}")
async def get_interview_schema(product_code: str, loan_type: str = Query(...)):
    """Interview slot schema for a product, keyed purely by product_code —
    no DB lookup. Lets a product sourced from an external catalog (the main
    platform's services/api) get an interview schema here without also
    existing as a row in this service's own products table. The caller
    already knows loan_type (from that catalog) and passes it through so
    unmatched product codes still get a sensible base interview (see
    slots/registry.py: unknown codes get the base slots, just no
    product-specific overlay)."""
    schema = schema_for(product_code)
    schema["loan_type"] = loan_type
    return schema


@app.get("/api/v1/loan-types/{loan_type}/categories/{category}/document-requirements")
async def get_document_requirements(
    loan_type: str,
    category: str,
    bank_id: str = Query(default=DEFAULT_BANK_ID),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(DocumentType.code, DocumentType.name)
        .join(
            DocumentRequirement,
            (DocumentRequirement.document_type_code == DocumentType.code)
            & (DocumentRequirement.bank_id == DocumentType.bank_id),
        )
        .where(
            DocumentRequirement.bank_id == bank_id,
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


@app.get("/api/v1/policy/{key}")
async def get_policy(
    key: str,
    bank_id: str = Query(default=DEFAULT_BANK_ID),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(PolicySetting)
        .where(PolicySetting.bank_id == bank_id, PolicySetting.key == key)
        .order_by(PolicySetting.effective_from.desc())
    )
    result = await session.execute(stmt)
    setting = result.scalars().first()
    if setting is None:
        raise HTTPException(404, f"No policy setting for '{key}'")
    return {"key": setting.key, "version": setting.version, "document": setting.document}

@app.get("/api/v1/rules")
async def get_rules(
    framework: str | None = None,
    bank_id: str = Query(default=DEFAULT_BANK_ID),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Rule).where(Rule.bank_id == bank_id)
    if framework:
        stmt = stmt.where(Rule.framework == framework)
    result = await session.execute(stmt)
    rules_result = result.scalars().all()
    return {"rules": [{"rule_id": r.rule_id, "framework": r.framework, **r.document} for r in rules_result]}