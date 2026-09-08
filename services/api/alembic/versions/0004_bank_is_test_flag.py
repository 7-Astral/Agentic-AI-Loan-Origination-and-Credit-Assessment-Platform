"""add is_test flag to banks (lets test-created banks be filtered from user-facing lists)

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-31

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "banks",
        sa.Column("is_test", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("banks", "is_test")
