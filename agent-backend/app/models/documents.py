import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    verification_type: Mapped[str] = mapped_column(String(50))
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="uploaded")  # uploaded | extracted | needs_reupload
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    extraction: Mapped["DocumentExtraction"] = relationship(back_populates="document", uselist=False)


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), unique=True)
    extracted_fields: Mapped[dict] = mapped_column(JSON)
    notes: Mapped[str] = mapped_column(String(500), default="")
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    document: Mapped["Document"] = relationship(back_populates="extraction")


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    slot_id: Mapped[str] = mapped_column(String(100))
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"))
    declared_value: Mapped[str] = mapped_column(String(500), default="")
    extracted_value: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(20))  # match | mismatch | on_file | missing
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)