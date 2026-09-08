import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.enums import ConversationStatus, LoanType, conversation_status_enum, loan_type_enum


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("banks.id"), nullable=False
    )
    # FK added when `users` landed — previously unconstrained and never populated by any
    # code path, so backfilling the constraint is safe.
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    # Set once a completed enquiry is promoted into a persisted Application (see
    # models/application.py) — the chat flow itself stays anonymous/unauthenticated for now.
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), nullable=True
    )
    selected_loan_type: Mapped[LoanType | None] = mapped_column(loan_type_enum, nullable=True)
    selected_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loan_products.id"), nullable=True
    )
    current_question_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    collected_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[ConversationStatus] = mapped_column(
        conversation_status_enum, nullable=False, default=ConversationStatus.active
    )
    # Soft-delete: "deleting" an application from the frontend sets this rather than
    # removing the row, so application/audit data is never permanently lost.
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
