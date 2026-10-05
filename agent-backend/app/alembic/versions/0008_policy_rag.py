from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OPERATIONAL = "operational"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "policy_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("bank", sa.String(255), nullable=False, index=True),
        sa.Column("bank_type", sa.String(100), nullable=True),
        sa.Column("loan_type", sa.String(255), nullable=False, index=True),
        sa.Column("category", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("data_status", sa.String(100), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=OPERATIONAL,
    )


def downgrade() -> None:
    op.drop_table("policy_chunks", schema=OPERATIONAL)
