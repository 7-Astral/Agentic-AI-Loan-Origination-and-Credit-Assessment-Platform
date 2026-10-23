from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '4d5e6f7a8b9c'
down_revision: Union[str, None] = '3c4d5e6f7a8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.add_column("loan_applications", sa.Column("applicant_legal_name", sa.String(200), nullable=True))
    op.add_column("loan_applications", sa.Column("assessment_tier", sa.String(30), nullable=True))
    op.add_column("loan_applications", sa.Column("assessment_score", sa.Numeric(5, 1), nullable=True))


def downgrade() -> None:
    op.drop_column("loan_applications", "assessment_score")
    op.drop_column("loan_applications", "assessment_tier")
    op.drop_column("loan_applications", "applicant_legal_name")
