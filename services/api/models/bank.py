import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.enums import BankStatus, bank_status_enum


class Bank(Base):
    __tablename__ = "banks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    branding: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[BankStatus] = mapped_column(
        bank_status_enum, nullable=False, default=BankStatus.active
    )
    # Set True only by test fixtures (this repo's tests write to the configured
    # DATABASE_URL directly rather than an isolated test DB — see tests/conftest.py).
    # Lets banks/conversations created by test runs be filtered out of user-facing lists
    # without having to delete them.
    is_test: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
