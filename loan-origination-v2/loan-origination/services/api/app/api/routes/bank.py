import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_labels import resolve_entity_labels
from app.core.config import settings
from app.core.deps import get_current_staff, get_current_user, require_bank_manager, require_bank_permission
from app.core.security import hash_password
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.bank_position import BankPosition
from app.models.enums import DecisionResult, DecisionType, EscalationStatus, LoanStatus, UserRole
from app.models.escalation import Escalation
from app.models.lending_policy import LendingPolicy
from app.models.loan_application import LoanApplication
from app.models.loan_decision import LoanDecision
from app.models.loan_product import LoanProduct, generate_product_code
from app.models.notification import Notification
from app.models.user import User
from app.schemas.admin import AuditLogOut, LendingPolicyOut, LoanProductOut
from app.schemas.auth import UserOut
from app.schemas.bank import (
    ApplicationDecisionRequest,
    ApplicationDecisionOut,
    BankPositionOut,
    CreateBankStaffRequest,
    CreateLendingPolicyRequest,
    CreateLoanProductRequest,
    LoanApplicationOut,
    NotificationOut,
    UpdateBankStaffRequest,
    UpdateLendingPolicyRequest,
    UpdateLoanProductRequest,
)

router = APIRouter()


@router.get("/positions", response_model=list[BankPositionOut])
async def list_positions(staff: User = Depends(get_current_staff), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BankPosition).where(BankPosition.bank_id == staff.bank_id).order_by(BankPosition.rank.asc()))
    return result.scalars().all()


@router.get("/staff", response_model=list[UserOut])
async def list_bank_staff(staff: User = Depends(get_current_staff), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.bank_id == staff.bank_id, User.role == UserRole.STAFF.value).order_by(User.created_at)
    )
    return result.scalars().all()


@router.post("/staff", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_bank_staff(
    payload: CreateBankStaffRequest,
    actor: User = Depends(require_bank_permission("can_manage_staff")),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    position = await db.get(BankPosition, payload.position_id)
    if position is None or position.bank_id != actor.bank_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Position not found for your bank")

    staff = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.STAFF.value,
        bank_id=actor.bank_id,
        position_id=payload.position_id,
    )
    db.add(staff)
    await db.flush()

    db.add(
        AuditLog(
            bank_id=actor.bank_id,
            entity_type="user",
            entity_id=str(staff.id),
            action="staff_created",
            performed_by=actor.id,
            after_state={"email": staff.email, "full_name": staff.full_name, "position": position.title},
        )
    )
    await db.commit()
    await db.refresh(staff)
    return staff


@router.patch("/staff/{staff_id}", response_model=UserOut)
async def update_bank_staff(
    staff_id: uuid.UUID,
    payload: UpdateBankStaffRequest,
    actor: User = Depends(require_bank_permission("can_manage_staff")),
    db: AsyncSession = Depends(get_db),
):
    """Edit a staff member's name and/or position. Not for activation state —
    use the deactivate/reactivate routes for that — and there's deliberately
    no DELETE: a staff record stays around (deactivated) so past decisions,
    escalations and audit entries it's tied to still resolve to someone."""
    target = await db.get(User, staff_id)
    if target is None or target.role != UserRole.STAFF.value or target.bank_id != actor.bank_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")

    updates = payload.model_dump(exclude_unset=True)
    if "position_id" in updates and updates["position_id"] is not None:
        position = await db.get(BankPosition, updates["position_id"])
        if position is None or position.bank_id != actor.bank_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Position not found for your bank")

    if not updates:
        return target

    for field, value in updates.items():
        setattr(target, field, value)

    db.add(
        AuditLog(
            bank_id=actor.bank_id,
            entity_type="user",
            entity_id=str(target.id),
            action="staff_updated",
            performed_by=actor.id,
            after_state={k: str(v) for k, v in updates.items()},
        )
    )
    await db.commit()
    await db.refresh(target)
    return target


@router.post("/staff/{staff_id}/deactivate", response_model=UserOut)
async def deactivate_bank_staff(
    staff_id: uuid.UUID,
    actor: User = Depends(require_bank_permission("can_manage_staff")),
    db: AsyncSession = Depends(get_db),
):
    if staff_id == actor.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate your own account")

    target = await db.get(User, staff_id)
    if target is None or target.role != UserRole.STAFF.value or target.bank_id != actor.bank_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")

    if target.is_active:
        target.is_active = False
        db.add(
            AuditLog(
                bank_id=actor.bank_id,
                entity_type="user",
                entity_id=str(target.id),
                action="staff_deactivated",
                performed_by=actor.id,
                after_state={"email": target.email, "is_active": False},
            )
        )
        await db.commit()
        await db.refresh(target)
    return target


@router.post("/staff/{staff_id}/reactivate", response_model=UserOut)
async def reactivate_bank_staff(
    staff_id: uuid.UUID,
    actor: User = Depends(require_bank_permission("can_manage_staff")),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(User, staff_id)
    if target is None or target.role != UserRole.STAFF.value or target.bank_id != actor.bank_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")

    if not target.is_active:
        target.is_active = True
        db.add(
            AuditLog(
                bank_id=actor.bank_id,
                entity_type="user",
                entity_id=str(target.id),
                action="staff_reactivated",
                performed_by=actor.id,
                after_state={"email": target.email, "is_active": True},
            )
        )
        await db.commit()
        await db.refresh(target)
    return target


@router.get("/loan-products", response_model=list[LoanProductOut])
async def list_bank_products(staff: User = Depends(get_current_staff), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LoanProduct).where(LoanProduct.bank_id == staff.bank_id).order_by(LoanProduct.name))
    return result.scalars().all()


@router.post("/loan-products", response_model=LoanProductOut, status_code=status.HTTP_201_CREATED)
async def create_bank_product(
    payload: CreateLoanProductRequest,
    actor: User = Depends(require_bank_permission("can_manage_products")),
    db: AsyncSession = Depends(get_db),
):
    # product_code is NOT NULL + unique at the DB level (see migration
    # 0f8bc6a836fe), so it must be set on the INSERT itself — generate the
    # id ourselves up front instead of relying on a post-flush id.
    product_id = uuid.uuid4()
    product = LoanProduct(
        id=product_id,
        bank_id=actor.bank_id,
        product_code=generate_product_code(payload.product_type, product_id),
        **payload.model_dump(),
    )
    db.add(product)
    await db.flush()
    db.add(
        AuditLog(
            bank_id=actor.bank_id,
            entity_type="loan_product",
            entity_id=str(product.id),
            action="product_created",
            performed_by=actor.id,
            after_state={"name": product.name, "product_type": product.product_type},
        )
    )
    await db.commit()
    await db.refresh(product)
    return product


@router.patch("/loan-products/{product_id}", response_model=LoanProductOut)
async def update_bank_product(
    product_id: uuid.UUID,
    payload: UpdateLoanProductRequest,
    actor: User = Depends(require_bank_permission("can_manage_products")),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(LoanProduct, product_id)
    if product is None or product.bank_id != actor.bank_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return product

    for field, value in updates.items():
        setattr(product, field, value)

    db.add(
        AuditLog(
            bank_id=actor.bank_id,
            entity_type="loan_product",
            entity_id=str(product.id),
            action="product_updated",
            performed_by=actor.id,
            after_state={k: str(v) for k, v in updates.items()},
        )
    )
    await db.commit()
    await db.refresh(product)
    return product


@router.post("/loan-products/{product_id}/deactivate", response_model=LoanProductOut)
async def deactivate_bank_product(
    product_id: uuid.UUID,
    actor: User = Depends(require_bank_permission("can_manage_products")),
    db: AsyncSession = Depends(get_db),
):
    """Products are never hard-deleted — past applications and lending
    policies reference them, and the chat agent's catalog client reads them
    by code. Deactivating just hides a product from new applications (see
    core-banking's product listing, which already filters on is_active)."""
    product = await db.get(LoanProduct, product_id)
    if product is None or product.bank_id != actor.bank_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if product.is_active:
        product.is_active = False
        db.add(
            AuditLog(
                bank_id=actor.bank_id,
                entity_type="loan_product",
                entity_id=str(product.id),
                action="product_deactivated",
                performed_by=actor.id,
                after_state={"is_active": False},
            )
        )
        await db.commit()
        await db.refresh(product)
    return product


@router.post("/loan-products/{product_id}/reactivate", response_model=LoanProductOut)
async def reactivate_bank_product(
    product_id: uuid.UUID,
    actor: User = Depends(require_bank_permission("can_manage_products")),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(LoanProduct, product_id)
    if product is None or product.bank_id != actor.bank_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if not product.is_active:
        product.is_active = True
        db.add(
            AuditLog(
                bank_id=actor.bank_id,
                entity_type="loan_product",
                entity_id=str(product.id),
                action="product_reactivated",
                performed_by=actor.id,
                after_state={"is_active": True},
            )
        )
        await db.commit()
        await db.refresh(product)
    return product


@router.get("/lending-policies", response_model=list[LendingPolicyOut])
async def list_bank_policies(staff: User = Depends(get_current_staff), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LendingPolicy).where(LendingPolicy.bank_id == staff.bank_id))
    return result.scalars().all()


@router.post("/lending-policies", response_model=LendingPolicyOut, status_code=status.HTTP_201_CREATED)
async def create_bank_policy(
    payload: CreateLendingPolicyRequest,
    actor: User = Depends(require_bank_permission("can_manage_products")),
    db: AsyncSession = Depends(get_db),
):
    if payload.product_id is not None:
        product = await db.get(LoanProduct, payload.product_id)
        if product is None or product.bank_id != actor.bank_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product not found for your bank")

    policy = LendingPolicy(bank_id=actor.bank_id, updated_by=actor.id, **payload.model_dump())
    db.add(policy)
    await db.flush()
    db.add(
        AuditLog(
            bank_id=actor.bank_id,
            entity_type="lending_policy",
            entity_id=str(policy.id),
            action="policy_created",
            performed_by=actor.id,
            after_state={"auto_approval_max_amount": payload.auto_approval_max_amount},
        )
    )
    await db.commit()
    await db.refresh(policy)
    return policy


@router.patch("/lending-policies/{policy_id}", response_model=LendingPolicyOut)
async def update_bank_policy(
    policy_id: uuid.UUID,
    payload: UpdateLendingPolicyRequest,
    actor: User = Depends(require_bank_permission("can_manage_products")),
    db: AsyncSession = Depends(get_db),
):
    policy = await db.get(LendingPolicy, policy_id)
    if policy is None or policy.bank_id != actor.bank_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    updates = payload.model_dump(exclude_unset=True)
    if "product_id" in updates and updates["product_id"] is not None:
        product = await db.get(LoanProduct, updates["product_id"])
        if product is None or product.bank_id != actor.bank_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product not found for your bank")

    if not updates:
        return policy

    for field, value in updates.items():
        setattr(policy, field, value)
    policy.updated_by = actor.id

    db.add(
        AuditLog(
            bank_id=actor.bank_id,
            entity_type="lending_policy",
            entity_id=str(policy.id),
            action="policy_updated",
            performed_by=actor.id,
            after_state={k: str(v) for k, v in updates.items()},
        )
    )
    await db.commit()
    await db.refresh(policy)
    return policy


@router.post("/lending-policies/{policy_id}/deactivate", response_model=LendingPolicyOut)
async def deactivate_bank_policy(
    policy_id: uuid.UUID,
    actor: User = Depends(require_bank_permission("can_manage_products")),
    db: AsyncSession = Depends(get_db),
):
    """Policies are never hard-deleted — see _applicable_policy in
    app.core.lending_logic, which now only considers is_active policies, so
    deactivating one immediately stops it from governing new decisions
    without losing the historical record of what it was."""
    policy = await db.get(LendingPolicy, policy_id)
    if policy is None or policy.bank_id != actor.bank_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    if policy.is_active:
        policy.is_active = False
        db.add(
            AuditLog(
                bank_id=actor.bank_id,
                entity_type="lending_policy",
                entity_id=str(policy.id),
                action="policy_deactivated",
                performed_by=actor.id,
                after_state={"is_active": False},
            )
        )
        await db.commit()
        await db.refresh(policy)
    return policy


@router.post("/lending-policies/{policy_id}/reactivate", response_model=LendingPolicyOut)
async def reactivate_bank_policy(
    policy_id: uuid.UUID,
    actor: User = Depends(require_bank_permission("can_manage_products")),
    db: AsyncSession = Depends(get_db),
):
    policy = await db.get(LendingPolicy, policy_id)
    if policy is None or policy.bank_id != actor.bank_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    if not policy.is_active:
        policy.is_active = True
        db.add(
            AuditLog(
                bank_id=actor.bank_id,
                entity_type="lending_policy",
                entity_id=str(policy.id),
                action="policy_reactivated",
                performed_by=actor.id,
                after_state={"is_active": True},
            )
        )
        await db.commit()
        await db.refresh(policy)
    return policy


@router.get("/loan-applications", response_model=list[LoanApplicationOut])
async def list_bank_applications(staff: User = Depends(get_current_staff), db: AsyncSession = Depends(get_db)):
    apps_result = await db.execute(
        select(LoanApplication).where(LoanApplication.bank_id == staff.bank_id).order_by(LoanApplication.created_at.desc())
    )
    applications = apps_result.scalars().all()
    if not applications:
        return []

    esc_result = await db.execute(
        select(Escalation, BankPosition)
        .join(BankPosition, Escalation.escalated_to_position_id == BankPosition.id, isouter=True)
        .where(Escalation.application_id.in_([a.id for a in applications]), Escalation.status == "pending")
    )
    position_by_app = {esc.application_id: (pos.title if pos else None) for esc, pos in esc_result.all()}

    applicants_result = await db.execute(
        select(User).where(User.id.in_({a.applicant_id for a in applications}))
    )
    applicant_by_id = {u.id: u for u in applicants_result.scalars().all()}

    out = []
    for app in applications:
        item = LoanApplicationOut.model_validate(app)
        item.pending_position_title = position_by_app.get(app.id)
        applicant = applicant_by_id.get(app.applicant_id)
        if applicant:
            item.applicant_name = applicant.full_name
            item.applicant_email = applicant.email
        out.append(item)
    return out


@router.post("/loan-applications/{application_id}/decision", response_model=ApplicationDecisionOut)
async def decide_loan_application(
    application_id: uuid.UUID,
    payload: ApplicationDecisionRequest,
    staff: User = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """A staff member's manual approve/reject on an escalated application —
    the human-review step at the end of route_loan_decision's ladder (see
    app.core.lending_logic). Works the same for a chat-originated
    application as for the plain form: both land in loan_applications and
    go through the same escalation, so there's nothing chat-specific here."""
    if payload.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="decision must be 'approved' or 'rejected'")

    application = await db.get(LoanApplication, application_id)
    if application is None or application.bank_id != staff.bank_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if application.status != LoanStatus.UNDER_REVIEW.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Application is '{application.status}', not awaiting a decision",
        )

    esc_result = await db.execute(
        select(Escalation).where(
            Escalation.application_id == application_id, Escalation.status == EscalationStatus.PENDING.value
        )
    )
    escalation = esc_result.scalar_one_or_none()

    # Only the position this was escalated to may act on it — unless the
    # acting staff member holds a position with unlimited approval authority
    # (max_approval_amount is None), which can act at any rung below it.
    if escalation and escalation.escalated_to_position_id and staff.position_id != escalation.escalated_to_position_id:
        staff_position = await db.get(BankPosition, staff.position_id) if staff.position_id else None
        if staff_position is None or staff_position.max_approval_amount is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This application is pending a different position's approval",
            )

    approved = payload.decision == "approved"
    result = DecisionResult.APPROVED.value if approved else DecisionResult.REJECTED.value
    application.status = LoanStatus.APPROVED.value if approved else LoanStatus.REJECTED.value

    db.add(
        LoanDecision(
            application_id=application.id,
            decision=result,
            decision_type=DecisionType.MANUAL.value,
            approved_amount=(payload.approved_amount or float(application.requested_amount)) if approved else None,
            decided_by=staff.id,
            decision_reason=payload.reason,
        )
    )

    if escalation:
        escalation.status = EscalationStatus.RESOLVED.value
        escalation.resolved_at = datetime.now(timezone.utc)

    db.add(
        AuditLog(
            bank_id=staff.bank_id,
            entity_type="loan_application",
            entity_id=str(application.id),
            action=f"staff_{payload.decision}",
            performed_by=staff.id,
            after_state={"decision": payload.decision, "reason": payload.reason},
        )
    )
    db.add(
        Notification(
            user_id=application.applicant_id,
            title="Your loan application was approved" if approved else "Your loan application was declined",
            message=(
                f"Your ${float(application.requested_amount):,.0f} application was approved."
                if approved
                else f"Your ${float(application.requested_amount):,.0f} application was declined."
            )
            + (f" {payload.reason}" if payload.reason else ""),
            entity_type="loan_application",
            entity_id=str(application.id),
        )
    )

    await db.commit()
    await db.refresh(application)

    return ApplicationDecisionOut(
        application_id=application.id,
        status=application.status,
        decision=result,
        decided_at=datetime.now(timezone.utc),
    )


@router.get("/loan-applications/{application_id}/chat-report")
async def get_application_chat_report(
    application_id: uuid.UUID,
    staff: User = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Proxies to the chat-agent backend for the full interview report
    (transcript-derived slots, Five C's assessment, document checklist,
    decision history) behind a chat-originated application — only staff at
    the owning bank can view it, and only for applications that actually
    came in through the chat assistant."""
    application = await db.get(LoanApplication, application_id)
    if application is None or application.bank_id != staff.bank_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if not application.chat_session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This application wasn't submitted via the chat assistant",
        )

    url = f"{settings.agent_backend_base_url}/api/v1/applications/{application.chat_session_id}/report"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers={"X-API-Key": settings.service_api_key})
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Chat assistant service returned an error: {exc.response.text}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat assistant service is unavailable",
        ) from exc

    return resp.json()


@router.get("/audit-logs", response_model=list[AuditLogOut])
async def list_bank_audit_logs(staff: User = Depends(require_bank_manager), db: AsyncSession = Depends(get_db)):
    """A bank manager's view of their own bank's activity — staff added or
    changed, products/policies created or (de)activated, applications
    decided or submitted. Manager-only (require_bank_manager: needs both
    can_manage_staff and can_manage_products), unlike Team/Products/Policies
    which each only need one of those flags — this surfaces everything, so
    it's gated on holding full authority, not partial."""
    result = await db.execute(
        select(AuditLog).where(AuditLog.bank_id == staff.bank_id).order_by(AuditLog.created_at.desc()).limit(200)
    )
    logs = result.scalars().all()
    labels = await resolve_entity_labels(db, logs)
    return [
        AuditLogOut.model_validate(log).model_copy(
            update={"entity_label": labels.get((log.entity_type, log.entity_id))}
        )
        for log in logs
    ]


@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(50)
    )
    return result.scalars().all()


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_read(
    notification_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    notification = await db.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return notification
