import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

EMBEDDING_DIMENSIONS = 384


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PolicyChunk(Base):
    __tablename__ = "policy_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank: Mapped[str] = mapped_column(String(255), index=True)
    bank_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    loan_type: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(255), default="banks_policy.csv")
    data_status: Mapped[str] = mapped_column(String(100), default="synthetic_demo_policy")
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
