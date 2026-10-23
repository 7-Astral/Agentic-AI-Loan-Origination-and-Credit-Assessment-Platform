"""add bank_id to audit_logs

Revision ID: 3c4d5e6f7a8b
Revises: 2b3c4d5e6f7a
Create Date: 2026-09-19 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '3c4d5e6f7a8b'
down_revision = '2b3c4d5e6f7a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Lets a bank manager (see require_bank_manager) view just their own
    # bank's activity via GET /bank/audit-logs — audit_logs previously had
    # no way to attribute an entry to a bank at all. Nullable: some actions
    # (e.g. a platform admin managing another admin account) genuinely
    # aren't scoped to any bank.
    op.add_column(
        "audit_logs",
        sa.Column("bank_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("banks.id"), nullable=True),
    )
    op.create_index("ix_audit_logs_bank_id", "audit_logs", ["bank_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_bank_id", table_name="audit_logs")
    op.drop_column("audit_logs", "bank_id")
