"""add chat_session_id to loan_applications

Revision ID: 1a2b3c4d5e6f
Revises: 0f8bc6a836fe
Create Date: 2026-09-14 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
down_revision = '0f8bc6a836fe'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Links a platform loan_applications row back to the agent-backend chat
    # session (its Application.id) it was submitted from, when it was
    # submitted via the chat assistant rather than the plain apply form —
    # lets staff open the full interview/assessment/document report for
    # that session (see services/api's GET /bank/loan-applications/{id}/chat-report).
    op.add_column(
        "loan_applications", sa.Column("chat_session_id", sa.String(length=64), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("loan_applications", "chat_session_id")
