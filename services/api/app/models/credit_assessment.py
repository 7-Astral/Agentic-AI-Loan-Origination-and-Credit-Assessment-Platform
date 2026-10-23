import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CreditAssessment(Base):
    """Immutable — one row per assessment run. Never update in place; insert a new
    row for a re-assessment. This is the audit trail (FR11 compliance)."""

    __tablename__ = "credit_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loan_applications.id"), nullable=False
    )
    credit_score: Mapped[int] = mapped_column(Integer, nullable=False)
    bureau_source: Mapped[str] = mapped_column(String(100), nullable=False, default="mock_bureau")
    risk_rating: Mapped[str] = mapped_column(String(20), nullable=False)
    dti_ratio: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    assessment_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
