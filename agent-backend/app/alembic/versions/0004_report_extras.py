from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OPERATIONAL = "operational"


def upgrade() -> None:
    op.add_column("assessment_results", sa.Column("narrative_summary", sa.Text(), nullable=True), schema=OPERATIONAL)
    op.add_column(
        "assessment_results", sa.Column("narrative_summary_score", sa.Float(), nullable=True), schema=OPERATIONAL,
    )


def downgrade() -> None:
    op.drop_column("assessment_results", "narrative_summary_score", schema=OPERATIONAL)
    op.drop_column("assessment_results", "narrative_summary", schema=OPERATIONAL)
