"""drop identity fk on applicant_id

Revision ID: 2e0461e0964e
Revises: 0001
Create Date: 2026-09-11 09:04:22.114882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e0461e0964e'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "applications_applicant_id_fkey", "applications", schema="operational", type_="foreignkey"
    )


def downgrade() -> None:
    op.create_foreign_key(
        "applications_applicant_id_fkey",
        "applications",
        "users",
        ["applicant_id"],
        ["id"],
        source_schema="operational",
        referent_schema="identity",
    )
