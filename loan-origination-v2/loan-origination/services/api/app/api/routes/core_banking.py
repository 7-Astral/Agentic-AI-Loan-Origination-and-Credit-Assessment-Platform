"""Core-banking-style catalog contract.

Exposes this platform's own loan_products/banks tables through the same
request/response shape the chat-agent backend's CoreBankingClient already
speaks to mock_core_banking's public API (see product_to_dict() in that
project's mock_core_banking/main.py). This makes this platform the single
source of truth for the product catalog: the agent's catalog client is
repointed here, while document-requirement checklists, HEM/shading policy
and the Five C's rules stay served by mock_core_banking, since those are
assessment configuration rather than staff-managed catalog data.

Server-to-server only — callers authenticate with a shared X-API-Key
(see app.core.deps.require_service_api_key), not a user JWT.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_service_api_key
from app.core.lending_logic import route_loan_decision
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.bank import Bank
from app.models.enums import UserRole
from app.models.loan_application import LoanApplication
from app.models.loan_product import LoanProduct
from app.models.user import User
from app.schemas.core_banking import SubmitApplicationRequest, SubmitApplicationResponse

router = APIRouter(prefix="/api/v1", tags=["core-banking"], dependencies=[Depends(require_service_api_key)])

# Maps this platform's product_type values onto the loan_type/category
# vocabulary mock_core_banking's document-requirements, policy and rules
# config already use (see mock_core_banking/seed.py in agent-backend).
# "education" has no dedicated config there, so it falls back to the
# closest fit (personal/general, unsecured general-purpose) — an explicit,
# documented simplification, not a silent gap.
LOAN_TYPE_INFO = {
    "personal": {"name": "Personal Loan", "description": "Unsecured or secured loan for personal use."},
    "home": {"name": "Home Loan", "description": "Loan to buy, refinance, or invest in residential property."},
    "business": {"name": "Business Loan", "description": "Term finance for business purposes."},
}
CATEGORY_NAMES = {
    "general": "General",
    "vehicle": "Vehicle",
    "owner_occupied": "Owner Occupied",
    "investment": "Investment",
    "term": "Term",
}
PRODUCT_TYPE_MAP: dict[str, tuple[str, str]] = {
    "personal": ("personal", "general"),
    "auto": ("personal", "vehicle"),
    "home": ("home", "owner_occupied"),
    "business": ("business", "term"),
    "education": ("personal", "general"),
}


def _product_to_dict(p: LoanProduct) -> dict:
    loan_type, category = PRODUCT_TYPE_MAP.get(p.product_type, ("personal", "general"))
    comparison_rate = p.comparison_rate if p.comparison_rate is not None else p.interest_rate_max
    return {
        "product_code": p.product_code,
        "name": p.name,
        "loan_type": loan_type,
        "category": category,
        "secured": p.secured,
        "min_amount": float(p.min_amount),
        "max_amount": float(p.max_amount),
        "min_term_months": p.tenure_min_months,
        "max_term_months": p.tenure_max_months,
        "interest_rate": float(p.interest_rate_min),
        "comparison_rate": float(comparison_rate),
        "rate_type": p.rate_type,
        "establishment_fee": float(p.establishment_fee),
        "max_lvr": p.max_lvr,
        "features": p.features or [],
    }


@router.get("/banks/by-code/{code}")
async def get_bank_by_code(code: str, db: AsyncSession = Depends(get_db)):
    """Resolves a bank's id from its stable code (e.g. 'FNB001') — lets
    services/agent-backend avoid hardcoding a bank_id UUID that changes
    every time the database is wiped and reseeded."""
    result = await db.execute(select(Bank).where(Bank.code == code))
    bank = result.scalar_one_or_none()
    if bank is None:
        raise HTTPException(404, f"Bank with code '{code}' not found")
    return {"id": str(bank.id), "name": bank.name, "code": bank.code}


async def _active_products(db: AsyncSession, bank_id: uuid.UUID) -> list[LoanProduct]:
    result = await db.execute(
        select(LoanProduct).where(LoanProduct.bank_id == bank_id, LoanProduct.is_active.is_(True))
    )
    return list(result.scalars().all())


@router.get("/loan-types")
async def list_loan_types(bank_id: uuid.UUID = Query(...), db: AsyncSession = Depends(get_db)):
    products = await _active_products(db, bank_id)

    grouped: dict[str, set[str]] = {}
    for p in products:
        loan_type, category = PRODUCT_TYPE_MAP.get(p.product_type, ("personal", "general"))
        grouped.setdefault(loan_type, set()).add(category)

    loan_types = []
    for code, categories in grouped.items():
        info = LOAN_TYPE_INFO.get(code, {"name": code.title(), "description": ""})
        loan_types.append(
            {
                "code": code,
                "name": info["name"],
                "description": info["description"],
                "categories": [
                    {"code": c, "name": CATEGORY_NAMES.get(c, c.title())} for c in sorted(categories)
                ],
            }
        )
    return {"loan_types": loan_types}


@router.get("/products")
async def list_products(
    loan_type: str | None = Query(default=None),
    category: str | None = Query(default=None),
    bank_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    products = await _active_products(db, bank_id)

    items = []
    for p in products:
        mapped_loan_type, mapped_category = PRODUCT_TYPE_MAP.get(p.product_type, ("personal", "general"))
        if loan_type and mapped_loan_type != loan_type:
            continue
        if category and mapped_category != category:
            continue
        items.append(p)

    if not items:
        if loan_type and category:
            raise HTTPException(404, f"No products for category '{category}' under loan type '{loan_type}'")
        if loan_type:
            raise HTTPException(404, f"No products for loan type '{loan_type}'")
        if category:
            raise HTTPException(404, f"No products for category '{category}'")

    return {"count": len(items), "products": [_product_to_dict(p) for p in items]}


@router.get("/products/{product_code}")
async def get_product(product_code: str, bank_id: uuid.UUID = Query(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LoanProduct).where(
            LoanProduct.bank_id == bank_id,
            LoanProduct.product_code.ilike(product_code),
            LoanProduct.is_active.is_(True),
        )
    )
    p = result.scalar_one_or_none()
    if p is None:
        raise HTTPException(404, f"Product '{product_code}' not found")
    return _product_to_dict(p)


@router.post("/applications", response_model=SubmitApplicationResponse, status_code=201)
async def submit_application(
    payload: SubmitApplicationRequest, db: AsyncSession = Depends(get_db)
) -> SubmitApplicationResponse:
    """Hands a completed chat-agent interview into the real loan pipeline:
    creates a genuine loan_applications row and runs it through the same
    deterministic auto-approve/escalate routing (route_loan_decision) that
    the plain customer apply form uses, so it shows up for staff exactly the
    same way regardless of which front door the customer used."""
    result = await db.execute(
        select(LoanProduct).where(
            LoanProduct.bank_id == payload.bank_id,
            LoanProduct.product_code.ilike(payload.product_code),
            LoanProduct.is_active.is_(True),
        )
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(404, f"Product '{payload.product_code}' not found for this bank")
    if not (float(product.min_amount) <= payload.requested_amount <= float(product.max_amount)):
        raise HTTPException(
            400,
            f"Amount must be between ${product.min_amount:,.0f} and ${product.max_amount:,.0f} for this product",
        )

    applicant = await db.get(User, payload.applicant_id)
    if applicant is None or applicant.role != UserRole.CUSTOMER.value:
        raise HTTPException(404, "Applicant not found")

    application = LoanApplication(
        applicant_id=payload.applicant_id,
        bank_id=payload.bank_id,
        product_id=product.id,
        loan_type=product.product_type,
        requested_amount=payload.requested_amount,
        purpose=payload.purpose,
        tenure_requested_months=payload.tenure_requested_months,
        status="submitted",
        chat_session_id=payload.external_reference,
    )
    db.add(application)
    await db.flush()

    outcome = await route_loan_decision(db, application)

    db.add(
        AuditLog(
            bank_id=application.bank_id,
            entity_type="loan_application",
            entity_id=str(application.id),
            action="submitted_via_chat_agent",
            performed_by=payload.applicant_id,
            after_state={
                "requested_amount": payload.requested_amount,
                "outcome": outcome["outcome"],
                "chat_session_id": payload.external_reference,
            },
        )
    )
    await db.commit()
    await db.refresh(application)

    return SubmitApplicationResponse(
        application_id=application.id,
        status=application.status,
        outcome=outcome["outcome"],
        pending_position_title=(
            outcome["position"].title if outcome["outcome"] == "escalated" and outcome["position"] else None
        ),
    )
