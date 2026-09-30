"""Turns an audit_logs row's bare (entity_type, entity_id) into something a
person can actually read — a name, not a UUID fragment — and formats any
dollar amount involved (e.g. a loan application, a lending policy) as
currency rather than a raw number. Shared by both the platform-admin audit
view (routes/admin.py) and the bank-manager audit view (routes/bank.py).
"""
import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.bank import Bank
from app.models.bank_position import BankPosition
from app.models.lending_policy import LendingPolicy
from app.models.loan_application import LoanApplication
from app.models.loan_product import LoanProduct
from app.models.user import User


def _as_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None


def _money(amount) -> str:
    return f"${float(amount):,.0f}"


async def resolve_entity_labels(db: AsyncSession, logs: list[AuditLog]) -> dict[tuple[str, str], str]:
    """Batch-resolves every (entity_type, entity_id) pair found in `logs`
    into a human-readable label, with one query per entity_type (never one
    query per row). Missing/unresolvable ids are simply left out of the
    returned dict — callers fall back to the raw id when a key is absent.
    """
    ids_by_type: dict[str, set[uuid.UUID]] = defaultdict(set)
    for log in logs:
        entity_uuid = _as_uuid(log.entity_id)
        if entity_uuid is not None:
            ids_by_type[log.entity_type].add(entity_uuid)

    labels: dict[tuple[str, str], str] = {}

    if ids_by_type.get("user"):
        result = await db.execute(select(User).where(User.id.in_(ids_by_type["user"])))
        for user in result.scalars():
            labels[("user", str(user.id))] = user.full_name

    if ids_by_type.get("loan_product"):
        result = await db.execute(select(LoanProduct).where(LoanProduct.id.in_(ids_by_type["loan_product"])))
        for product in result.scalars():
            labels[("loan_product", str(product.id))] = product.name

    if ids_by_type.get("lending_policy"):
        result = await db.execute(
            select(LendingPolicy, LoanProduct.name)
            .outerjoin(LoanProduct, LoanProduct.id == LendingPolicy.product_id)
            .where(LendingPolicy.id.in_(ids_by_type["lending_policy"]))
        )
        for policy, product_name in result.all():
            scope = product_name or "Bank-wide"
            labels[("lending_policy", str(policy.id))] = f"{scope} — up to {_money(policy.auto_approval_max_amount)}"

    if ids_by_type.get("bank"):
        result = await db.execute(select(Bank).where(Bank.id.in_(ids_by_type["bank"])))
        for bank in result.scalars():
            labels[("bank", str(bank.id))] = bank.name

    if ids_by_type.get("bank_position"):
        result = await db.execute(select(BankPosition).where(BankPosition.id.in_(ids_by_type["bank_position"])))
        for position in result.scalars():
            labels[("bank_position", str(position.id))] = position.title

    if ids_by_type.get("loan_application"):
        result = await db.execute(
            select(LoanApplication).where(LoanApplication.id.in_(ids_by_type["loan_application"]))
        )
        for application in result.scalars():
            label = f"{application.loan_type.replace('_', ' ').title()} loan — {_money(application.requested_amount)}"
            labels[("loan_application", str(application.id))] = label

    return labels
