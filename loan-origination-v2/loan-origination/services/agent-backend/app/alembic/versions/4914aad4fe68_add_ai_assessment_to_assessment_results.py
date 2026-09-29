"""add ai_assessment to assessment_results

Revision ID: 4914aad4fe68
Revises: f37071924e93
Create Date: 2026-09-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4914aad4fe68'
down_revision: Union[str, None] = 'f37071924e93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assessment_results",
        sa.Column("ai_assessment", sa.JSON(), nullable=True),
        schema="operational",
    )


def downgrade() -> None:
    op.drop_column("assessment_results", "ai_assessment", schema="operational")
