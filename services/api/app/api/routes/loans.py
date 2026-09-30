from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.lending_logic import route_loan_decision
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.loan_application import LoanApplication
from app.models.loan_product import LoanProduct
from app.models.user import User
from app.schemas.admin import LoanProductOut
from app.schemas.bank import LoanApplicationOut, LoanApplyRequest

router = APIRouter()


@router.get("/products", response_model=list[LoanProductOut])
async def browse_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LoanProduct).where(LoanProduct.is_active.is_(True)).order_by(LoanProduct.name))
    return result.scalars().all()


@router.post("/apply", response_model=LoanApplicationOut, status_code=status.HTTP_201_CREATED)
async def apply_for_loan(
    payload: LoanApplyRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    if user.role != UserRole.CUSTOMER.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customers can apply for loans")

    product = await db.get(LoanProduct, payload.product_id)
    if product is None or product.bank_id != payload.bank_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Loan product not found for this bank")
    if not (float(product.min_amount) <= payload.requested_amount <= float(product.max_amount)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Amount must be between ${product.min_amount:,.0f} and ${product.max_amount:,.0f} for this product",
        )

    application = LoanApplication(
        applicant_id=user.id,
        bank_id=payload.bank_id,
        product_id=payload.product_id,
        loan_type=product.product_type,
        requested_amount=payload.requested_amount,
        purpose=payload.purpose,
        tenure_requested_months=payload.tenure_requested_months,
        status="submitted",
    )
    db.add(application)
    await db.flush()

    outcome = await route_loan_decision(db, application)

    db.add(
        AuditLog(
            bank_id=application.bank_id,
            entity_type="loan_application",
            entity_id=str(application.id),
            action="submitted",
            performed_by=user.id,
            after_state={"requested_amount": payload.requested_amount, "outcome": outcome["outcome"]},
        )
    )
    await db.commit()
    await db.refresh(application)

    result = LoanApplicationOut.model_validate(application)
    if outcome["outcome"] == "escalated" and outcome["position"]:
        result.pending_position_title = outcome["position"].title
    return result


@router.get("/my-applications", response_model=list[LoanApplicationOut])
async def my_applications(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LoanApplication).where(LoanApplication.applicant_id == user.id).order_by(LoanApplication.created_at.desc())
    )
    return result.scalars().all()
