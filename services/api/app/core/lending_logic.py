
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank_position import BankPosition
from app.models.enums import EscalationStatus, LoanStatus
from app.models.escalation import Escalation
from app.models.loan_application import LoanApplication
from app.models.notification import Notification
from app.models.user import User


async def route_loan_decision(db: AsyncSession, application: LoanApplication) -> dict:
    amount = float(application.requested_amount)

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
            f"Requires {target.title} approval for ${amount:,.0f} — every application needs a human decision"
            if target
            else f"${amount:,.0f} application needs a human decision; no approval ladder configured for this bank"
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
