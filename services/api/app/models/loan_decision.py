import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import DecisionResult, DecisionType


class LoanDecision(Base):
    __tablename__ = "loan_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loan_applications.id"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False, default=DecisionResult.PENDING.value)
    decision_type: Mapped[str] = mapped_column(String(10), nullable=False, default=DecisionType.AUTO.value)
    approved_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    approved_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    approved_tenure_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
