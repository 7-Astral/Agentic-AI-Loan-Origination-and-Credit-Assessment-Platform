import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import LoanType


class LoanProduct(Base):
    __tablename__ = "loan_products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("banks.id"), nullable=False)
    product_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    product_type: Mapped[str] = mapped_column(String(30), nullable=False, default=LoanType.PERSONAL.value)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    min_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    max_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    interest_rate_min: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    interest_rate_max: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    tenure_min_months: Mapped[int] = mapped_column(Integer, nullable=False)
    tenure_max_months: Mapped[int] = mapped_column(Integer, nullable=False)
    eligibility_criteria: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Catalog-contract fields (used by the /api/v1/products core-banking-style
    # endpoints so the chat agent's catalog client gets a fully-shaped product).
    secured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rate_type: Mapped[str] = mapped_column(String(20), default="variable", nullable=False)
    comparison_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    establishment_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    max_lvr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    features: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    bank: Mapped["Bank"] = relationship(back_populates="loan_products")


def generate_product_code(product_type: str, product_id: uuid.UUID) -> str:
    """Stable, human-readable code for a product (e.g. PERSONAL-A1B2C3D4).

    Used as the external "product_code" identifier in the core-banking-style
    catalog contract consumed by the chat agent (agent-backend). It never
    changes for a given product, so it's safe to persist in the agent's
    LangGraph checkpoint state and reference in document/assessment flows.
    """
    return f"{product_type.upper()}-{str(product_id).split('-')[0].upper()}"
