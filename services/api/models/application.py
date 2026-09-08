import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.enums import ApplicationStatus, application_status_enum

# Note: this is the *persisted* loan application record (status, officer actions, etc.) —
# unrelated to schemas/application.py's NormalizedApplication, which is the risk-assessment
# domain's transient input shape and is never itself stored. Its API schemas live in
# schemas/application_record.py to avoid the name clash.


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (Index("ix_applications_bank_id_status", "bank_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("banks.id"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loan_products.id"), nullable=False
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        application_status_enum, nullable=False, default=ApplicationStatus.draft
    )
    loan_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    loan_term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    purpose: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
