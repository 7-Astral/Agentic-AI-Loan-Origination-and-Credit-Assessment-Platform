import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.enums import UserRole, user_role_enum


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Null for platform-level admins; set for every bank-scoped role (customer, loan_officer,
    # credit_manager).
    bank_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("banks.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(user_role_enum, nullable=False)
    # The external subject claim once an Entra ID / Azure AD B2C provider lands — see
    # auth/providers.py. Null for locally-authenticated users.
    auth_provider_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # Local auth only — null when the user is authenticated by an external provider instead.
    # Never returned in any response schema; never logged.
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
