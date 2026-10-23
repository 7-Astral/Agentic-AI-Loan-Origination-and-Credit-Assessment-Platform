from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OPERATIONAL = "operational"


def upgrade() -> None:
    op.add_column("assessment_results", sa.Column("group_scores", sa.JSON(), nullable=True), schema=OPERATIONAL)
    op.add_column("assessment_results", sa.Column("overall_score", sa.Float(), nullable=True), schema=OPERATIONAL)
    op.add_column("assessment_results", sa.Column("weights_applied", sa.JSON(), nullable=True), schema=OPERATIONAL)
    op.add_column("assessment_results", sa.Column("score_bands_applied", sa.JSON(), nullable=True), schema=OPERATIONAL)
    op.add_column("assessment_results", sa.Column("tier", sa.String(30), nullable=True), schema=OPERATIONAL)
    op.add_column("assessment_results", sa.Column("data_completeness", sa.JSON(), nullable=True), schema=OPERATIONAL)
    op.create_index(
        "ix_assessment_results_tier", "assessment_results", ["tier"], schema=OPERATIONAL,
    )


def downgrade() -> None:
    op.drop_index("ix_assessment_results_tier", table_name="assessment_results", schema=OPERATIONAL)
    op.drop_column("assessment_results", "data_completeness", schema=OPERATIONAL)
    op.drop_column("assessment_results", "tier", schema=OPERATIONAL)
    op.drop_column("assessment_results", "score_bands_applied", schema=OPERATIONAL)
    op.drop_column("assessment_results", "weights_applied", schema=OPERATIONAL)
    op.drop_column("assessment_results", "overall_score", schema=OPERATIONAL)
    op.drop_column("assessment_results", "group_scores", schema=OPERATIONAL)
