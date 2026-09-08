"""add loan_type scoping to prompt_templates (loan-type-specific system prompt focus)

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Reuses the `loan_type` enum created in 0002 — create_type=False, no new type here.
loan_type = postgresql.ENUM(
    "home", "investment", "personal", "car", "business", name="loan_type", create_type=False
)


def upgrade() -> None:
    op.add_column("prompt_templates", sa.Column("loan_type", loan_type, nullable=True))


def downgrade() -> None:
    op.drop_column("prompt_templates", "loan_type")
