import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

DEFAULT_BANK_ID = "default"


STATUS_ORDER = [
    "discovery", "interview", "documents", "assessment",
    "underwriter_review", "approved", "declined", "withdrawn",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    bank_id: Mapped[str] = mapped_column(String(50), default=DEFAULT_BANK_ID)
    applicant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=True
    )
    product_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="discovery")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    turn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ApplicationSlot(Base):
    __tablename__ = "application_slots"
    __table_args__ = (
        UniqueConstraint("application_id", "slot_key", name="uq_application_slot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), index=True
    )
    slot_key: Mapped[str] = mapped_column(String(100))
    value: Mapped[Any] = mapped_column(JSON)
    source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    turn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class AssessmentResult(Base):
    """Append-only — every assessment run inserts a new row, never updates."""

    __tablename__ = "assessment_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), index=True
    )
    product_code: Mapped[str] = mapped_column(String(30))
    metrics: Mapped[dict] = mapped_column(JSON)
    metrics_computed: Mapped[int] = mapped_column(Integer)
    metrics_total: Mapped[int] = mapped_column(Integer)
    rule_results: Mapped[Any] = mapped_column(JSON)
    route: Mapped[Any] = mapped_column(JSON)
    group_scores: Mapped[Any] = mapped_column(JSON, nullable=True)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    weights_applied: Mapped[Any] = mapped_column(JSON, nullable=True)
    score_bands_applied: Mapped[Any] = mapped_column(JSON, nullable=True)
    tier: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    data_completeness: Mapped[Any] = mapped_column(JSON, nullable=True)
    conditions_of_approval: Mapped[Any] = mapped_column(JSON, nullable=True)
    narrative_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    narrative_summary_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Decision(Base):
    
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), index=True
    )
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=True
    )
    outcome: Mapped[str] = mapped_column(String(30))  # approved | declined | refer_to_underwriter | withdrawn
    reasoning: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
