"""track platform submission on application

Revision ID: f37071924e93
Revises: 2e0461e0964e
Create Date: 2026-09-11 09:09:22.118212

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f37071924e93'
down_revision: Union[str, None] = '2e0461e0964e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("platform_application_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        schema="operational",
    )
    op.add_column(
        "applications", sa.Column("platform_status", sa.String(30), nullable=True), schema="operational"
    )


def downgrade() -> None:
    op.drop_column("applications", "platform_status", schema="operational")
    op.drop_column("applications", "platform_application_id", schema="operational")
