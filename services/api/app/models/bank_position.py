import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BankPosition(Base):
    """A rung on a bank's approval ladder (e.g. Loan Officer, Credit Manager, CFO,
    CEO, Board). Configurable per bank rather than hardcoded, per FR1/FR10 —
    different institutions can define their own hierarchy and thresholds.

    max_approval_amount = None means unlimited authority (typically the Board).
    """

    __tablename__ = "bank_positions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("banks.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    max_approval_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    can_manage_staff: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_manage_products: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
