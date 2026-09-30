"""Decides what happens to a submitted loan application: auto-approve under the
bank's policy threshold (notifying the bank's manager(s) so they're not blind
to it), or route it to the lowest-authority position on the bank's approval
ladder whose limit actually covers the requested amount — notifying every
staff member who holds that position.

This is deliberately a plain function over the ORM session rather than a
background task/agent — it's the seed of what the Decision Agent (FR8) will
wrap later, but the routing logic itself doesn't need an LLM: it's a
deterministic policy lookup.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank_position import BankPosition
from app.models.enums import DecisionResult, DecisionType, EscalationStatus, LoanStatus
from app.models.escalation import Escalation
from app.models.lending_policy import LendingPolicy
from app.models.loan_application import LoanApplication
from app.models.loan_decision import LoanDecision
from app.models.notification import Notification
from app.models.user import User


async def _applicable_policy(db: AsyncSession, application: LoanApplication) -> LendingPolicy | None:
    result = await db.execute(
        select(LendingPolicy).where(
            LendingPolicy.bank_id == application.bank_id,
            LendingPolicy.is_active.is_(True),
            (LendingPolicy.product_id == application.product_id) | (LendingPolicy.product_id.is_(None)),
        )
    )
    policies = result.scalars().all()
    # Prefer a product-specific policy over a bank-wide default.
    product_specific = [p for p in policies if p.product_id == application.product_id]
    return product_specific[0] if product_specific else (policies[0] if policies else None)


async def route_loan_decision(db: AsyncSession, application: LoanApplication) -> dict:
    amount = float(application.requested_amount)
    policy = await _applicable_policy(db, application)

    if policy and amount <= float(policy.auto_approval_max_amount):
        decision = LoanDecision(
            application_id=application.id,
            decision=DecisionResult.APPROVED.value,
            decision_type=DecisionType.AUTO.value,
            approved_amount=application.requested_amount,
            decision_reason=f"Within auto-approval threshold (${policy.auto_approval_max_amount:,.0f})",
        )
        application.status = LoanStatus.APPROVED.value
        db.add(decision)

        # No human approved this one, so the bank's manager(s) — a position
        # with BOTH can_manage_staff and can_manage_products, same bar as
        # require_bank_manager — get a heads-up notification rather than
        # being left with no visibility into auto-approvals happening under
        # their own policy thresholds.
        manager_result = await db.execute(
            select(User)
            .join(BankPosition, BankPosition.id == User.position_id)
            .where(
                User.bank_id == application.bank_id,
                User.is_active.is_(True),
                BankPosition.can_manage_staff.is_(True),
                BankPosition.can_manage_products.is_(True),
            )
        )
        for manager in manager_result.scalars().all():
            db.add(
                Notification(
                    user_id=manager.id,
                    title="Loan auto-approved",
                    message=f"A ${amount:,.0f} loan application was auto-approved under your bank's lending policy.",
                    entity_type="loan_application",
                    entity_id=str(application.id),
                )
            )

        return {"outcome": "auto_approved", "position": None}

    positions_result = await db.execute(
        select(BankPosition).where(BankPosition.bank_id == application.bank_id).order_by(BankPosition.rank.asc())
    )
    positions = positions_result.scalars().all()
    target = next((p for p in positions if p.max_approval_amount is None or float(p.max_approval_amount) >= amount), None)
    if target is None and positions:
        target = positions[-1]  # nothing covers it outright — route to the most senior position anyway

    escalation = Escalation(
        application_id=application.id,
        escalated_to_position_id=target.id if target else None,
        reason=(
            f"Requires {target.title} approval — requested amount ${amount:,.0f} exceeds the auto-approval threshold"
            if target
            else f"Requested amount ${amount:,.0f} exceeds auto-approval threshold; no approval ladder configured for this bank"
        ),
        status=EscalationStatus.PENDING.value,
    )
    application.status = LoanStatus.UNDER_REVIEW.value
    db.add(escalation)

    if target:
        staff_result = await db.execute(
            select(User).where(User.bank_id == application.bank_id, User.position_id == target.id, User.is_active.is_(True))
        )
        for staff in staff_result.scalars().all():
            db.add(
                Notification(
                    user_id=staff.id,
                    title="Loan approval required",
                    message=f"A ${amount:,.0f} loan application requires your approval as {target.title}.",
                    entity_type="loan_application",
                    entity_id=str(application.id),
                )
            )

    return {"outcome": "escalated", "position": target}
