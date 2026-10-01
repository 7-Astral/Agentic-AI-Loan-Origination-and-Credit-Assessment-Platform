from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OPERATIONAL = "operational"


def upgrade() -> None:
    op.create_table(
        "information_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_id", UUID(as_uuid=True),
            sa.ForeignKey(f"{OPERATIONAL}.applications.id"), nullable=False, index=True,
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("document_code", sa.String(50), nullable=True),
        sa.Column("requested_by", sa.String(150), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("document_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        schema=OPERATIONAL,
    )


def downgrade() -> None:
    op.drop_table("information_requests", schema=OPERATIONAL)
