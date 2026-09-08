import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class CustomerProfile(Base):
    """A customer's declared financial position, kept separate from `users` so officer and
    admin accounts don't carry nullable financial columns.

    `liabilities` mirrors `schemas/application.py::ExistingDebt`'s shape —
    `{"loans": [{"type", "balance", "monthly_repayment"}], "bnpl_accounts": [...],
    "credit_cards": [...]}` — so the risk-assessment input builder in
    `routers/applications.py` can pass it through near-directly. `assets` is loosely shaped
    for now (e.g. `{"savings": ...}`) — a documented known gap, not deeply wired into every
    one of the 5 C's this pass.
    """

    __tablename__ = "customer_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    employment_status: Mapped[str | None] = mapped_column(String, nullable=True)
    income: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    expenses: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    assets: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    liabilities: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
