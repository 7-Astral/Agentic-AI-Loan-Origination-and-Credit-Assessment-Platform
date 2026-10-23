"""add is_active to lending_policies

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2026-09-15 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2b3c4d5e6f7a'
down_revision = '1a2b3c4d5e6f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Lending policies aren't hard-deletable from the staff UI (deleting one
    # out from under decision routing is dangerous — see
    # app.core.lending_logic._applicable_policy) — instead staff can
    # deactivate/reactivate them, same pattern as loan_products.is_active.
    op.add_column(
        "lending_policies",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("lending_policies", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_column("lending_policies", "is_active")
