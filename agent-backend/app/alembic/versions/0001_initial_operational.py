from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OPERATIONAL = "operational"
IDENTITY = "identity"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {OPERATIONAL}")
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {IDENTITY}")

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=True, unique=True),
        sa.Column("name", sa.String(150), nullable=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("bank_id", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=IDENTITY,
    )

    op.create_table(
        "applications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("bank_id", sa.String(50), nullable=False, server_default="default"),
        sa.Column("applicant_id", UUID(as_uuid=True), sa.ForeignKey(f"{IDENTITY}.users.id"), nullable=True),
        sa.Column("product_code", sa.String(30), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="discovery"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=OPERATIONAL,
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "application_id", UUID(as_uuid=True),
            sa.ForeignKey(f"{OPERATIONAL}.applications.id"), nullable=False, index=True,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("turn", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=OPERATIONAL,
    )

    op.create_table(
        "application_slots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "application_id", UUID(as_uuid=True),
            sa.ForeignKey(f"{OPERATIONAL}.applications.id"), nullable=False, index=True,
        ),
        sa.Column("slot_key", sa.String(100), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(30), nullable=True),
        sa.Column("turn", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("application_id", "slot_key", name="uq_application_slot"),
        schema=OPERATIONAL,
    )

    op.create_table(
        "assessment_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "application_id", UUID(as_uuid=True),
            sa.ForeignKey(f"{OPERATIONAL}.applications.id"), nullable=False, index=True,
        ),
        sa.Column("product_code", sa.String(30), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("metrics_computed", sa.Integer(), nullable=False),
        sa.Column("metrics_total", sa.Integer(), nullable=False),
        sa.Column("rule_results", sa.JSON(), nullable=True),
        sa.Column("route", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=OPERATIONAL,
    )

    op.create_table(
        "decisions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "application_id", UUID(as_uuid=True),
            sa.ForeignKey(f"{OPERATIONAL}.applications.id"), nullable=False, index=True,
        ),
        sa.Column("decided_by", UUID(as_uuid=True), sa.ForeignKey(f"{IDENTITY}.users.id"), nullable=True),
        sa.Column("outcome", sa.String(30), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False, server_default=""),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=OPERATIONAL,
    )

    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_id", UUID(as_uuid=True),
            sa.ForeignKey(f"{OPERATIONAL}.applications.id"), nullable=False, index=True,
        ),
        sa.Column("verification_type", sa.String(50), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="uploaded"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=OPERATIONAL,
    )

    op.create_table(
        "document_extractions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id", UUID(as_uuid=True),
            sa.ForeignKey(f"{OPERATIONAL}.documents.id"), nullable=False, unique=True,
        ),
        sa.Column("extracted_fields", sa.JSON(), nullable=False),
        sa.Column("notes", sa.String(500), nullable=False, server_default=""),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=OPERATIONAL,
    )

    op.create_table(
        "verification_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_id", UUID(as_uuid=True),
            sa.ForeignKey(f"{OPERATIONAL}.applications.id"), nullable=False, index=True,
        ),
        sa.Column("slot_id", sa.String(100), nullable=False),
        sa.Column(
            "document_id", UUID(as_uuid=True),
            sa.ForeignKey(f"{OPERATIONAL}.documents.id"), nullable=False,
        ),
        sa.Column("declared_value", sa.String(500), nullable=False, server_default=""),
        sa.Column("extracted_value", sa.String(500), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=OPERATIONAL,
    )


def downgrade() -> None:
    op.drop_table("verification_results", schema=OPERATIONAL)
    op.drop_table("document_extractions", schema=OPERATIONAL)
    op.drop_table("documents", schema=OPERATIONAL)
    op.drop_table("decisions", schema=OPERATIONAL)
    op.drop_table("assessment_results", schema=OPERATIONAL)
    op.drop_table("application_slots", schema=OPERATIONAL)
    op.drop_table("messages", schema=OPERATIONAL)
    op.drop_table("applications", schema=OPERATIONAL)
    op.drop_table("users", schema=IDENTITY)
    op.execute(f"DROP SCHEMA IF EXISTS {OPERATIONAL} CASCADE")
    op.execute(f"DROP SCHEMA IF EXISTS {IDENTITY} CASCADE")
