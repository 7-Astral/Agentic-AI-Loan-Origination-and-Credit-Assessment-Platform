"""add required_field_templates table (5 C's risk assessment field checklist)

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Reuses the `loan_type` enum created in 0002 — create_type=False, no new type here.
loan_type = postgresql.ENUM(
    "home", "investment", "personal", "car", "business", name="loan_type", create_type=False
)


def upgrade() -> None:
    op.create_table(
        "required_field_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("loan_type", loan_type, nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("fields", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("required_field_templates")
