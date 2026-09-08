import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.enums import LoanType, loan_type_enum


class RequiredFieldTemplate(Base):
    """Per-product-type checklist of application fields the 5 C's risk assessment expects,
    mirroring `QuestionTemplate`'s baseline (loan_type IS NULL) + type-specific,
    versioned/active-flagged shape so the checklist can change per loan product without a
    code change."""

    __tablename__ = "required_field_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_type: Mapped[LoanType | None] = mapped_column(loan_type_enum, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fields: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
