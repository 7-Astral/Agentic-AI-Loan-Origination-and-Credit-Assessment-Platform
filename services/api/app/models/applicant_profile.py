import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import EncryptedString
from app.models.enums import EmploymentType


class ApplicantProfile(Base):
    __tablename__ = "applicant_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    employer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    monthly_income: Mapped[str | None] = mapped_column(EncryptedString(255), nullable=True)
    existing_liabilities: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    national_id: Mapped[str | None] = mapped_column(EncryptedString(255), nullable=True)
