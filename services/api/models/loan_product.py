import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.enums import LoanType, loan_type_enum


class LoanProduct(Base):
    __tablename__ = "loan_products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("banks.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[LoanType] = mapped_column(loan_type_enum, nullable=False)
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    min_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    max_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    min_term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    max_term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    eligibility_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
