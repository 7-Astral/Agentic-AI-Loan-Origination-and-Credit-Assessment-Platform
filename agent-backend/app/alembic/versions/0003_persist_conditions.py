from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OPERATIONAL = "operational"


def upgrade() -> None:
    op.add_column(
        "assessment_results", sa.Column("conditions_of_approval", sa.JSON(), nullable=True), schema=OPERATIONAL,
    )


def downgrade() -> None:
    op.drop_column("assessment_results", "conditions_of_approval", schema=OPERATIONAL)
