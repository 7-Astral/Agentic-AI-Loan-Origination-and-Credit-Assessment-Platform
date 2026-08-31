"""add bank, loan product, question/prompt template, conversation and message tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# create_type=False: these are created explicitly (once) in upgrade()/downgrade() below,
# so op.create_table must not also try to auto-create them for its columns.
bank_status = postgresql.ENUM("active", "inactive", name="bank_status", create_type=False)
loan_type = postgresql.ENUM(
    "home", "investment", "personal", "car", "business", name="loan_type", create_type=False
)
conversation_status = postgresql.ENUM(
    "active", "completed", name="conversation_status", create_type=False
)
message_role = postgresql.ENUM("user", "assistant", name="message_role", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    bank_status.create(bind, checkfirst=True)
    loan_type.create(bind, checkfirst=True)
    conversation_status.create(bind, checkfirst=True)
    message_role.create(bind, checkfirst=True)

    op.create_table(
        "banks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column(
            "branding", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("status", bank_status, nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_banks_slug", "banks", ["slug"], unique=True)

    op.create_table(
        "loan_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "bank_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("banks.id"), nullable=False
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", loan_type, nullable=False),
        sa.Column("interest_rate", sa.Numeric(6, 3), nullable=False),
        sa.Column("min_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("max_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("min_term_months", sa.Integer(), nullable=False),
        sa.Column("max_term_months", sa.Integer(), nullable=False),
        sa.Column(
            "eligibility_rules",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_loan_products_bank_id", "loan_products", ["bank_id"])

    op.create_table(
        "question_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "bank_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("banks.id"), nullable=True
        ),
        sa.Column("loan_type", loan_type, nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("questions", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    op.create_table(
        "prompt_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "bank_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("banks.id"), nullable=True
        ),
        sa.Column("agent_name", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "bank_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("banks.id"), nullable=False
        ),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("selected_loan_type", loan_type, nullable=True),
        sa.Column(
            "selected_product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("loan_products.id"),
            nullable=True,
        ),
        sa.Column("current_question_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "collected_data",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", conversation_status, nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column("role", message_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("prompt_templates")
    op.drop_table("question_templates")
    op.drop_index("ix_loan_products_bank_id", table_name="loan_products")
    op.drop_table("loan_products")
    op.drop_index("ix_banks_slug", table_name="banks")
    op.drop_table("banks")

    bind = op.get_bind()
    message_role.drop(bind, checkfirst=True)
    conversation_status.drop(bind, checkfirst=True)
    loan_type.drop(bind, checkfirst=True)
    bank_status.drop(bind, checkfirst=True)
