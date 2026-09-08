"""add users, customer_profiles, applications, officer_actions; link conversations

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = postgresql.ENUM(
    "customer", "loan_officer", "credit_manager", "admin", name="user_role", create_type=False
)
application_status = postgresql.ENUM(
    "draft", "submitted", "in_review", "decided", name="application_status", create_type=False
)
officer_action_type = postgresql.ENUM(
    "approve", "reject", "override", "request_info", name="officer_action_type", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    application_status.create(bind, checkfirst=True)
    officer_action_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "bank_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("banks.id"), nullable=True
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("auth_provider_id", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "customer_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("employment_status", sa.String(), nullable=True),
        sa.Column("income", sa.Numeric(12, 2), nullable=True),
        sa.Column("expenses", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "assets", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "liabilities", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
    )
    op.create_unique_constraint("uq_customer_profiles_user_id", "customer_profiles", ["user_id"])

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "bank_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("banks.id"), nullable=False
        ),
        sa.Column(
            "customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("loan_products.id"),
            nullable=False,
        ),
        sa.Column("status", application_status, nullable=False, server_default="draft"),
        sa.Column("loan_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("loan_term_months", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_applications_customer_id", "applications", ["customer_id"])
    op.create_index("ix_applications_bank_id_status", "applications", ["bank_id", "status"])

    op.create_table(
        "officer_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("applications.id"),
            nullable=False,
        ),
        sa.Column(
            "officer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("action", officer_action_type, nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_officer_actions_application_id", "officer_actions", ["application_id"])

    op.add_column(
        "conversations",
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_conversations_application_id",
        "conversations",
        "applications",
        ["application_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_conversations_customer_id", "conversations", "users", ["customer_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_conversations_customer_id", "conversations", type_="foreignkey")
    op.drop_constraint("fk_conversations_application_id", "conversations", type_="foreignkey")
    op.drop_column("conversations", "application_id")

    op.drop_index("ix_officer_actions_application_id", table_name="officer_actions")
    op.drop_table("officer_actions")

    op.drop_index("ix_applications_bank_id_status", table_name="applications")
    op.drop_index("ix_applications_customer_id", table_name="applications")
    op.drop_table("applications")

    op.drop_constraint("uq_customer_profiles_user_id", "customer_profiles", type_="unique")
    op.drop_table("customer_profiles")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    officer_action_type.drop(bind, checkfirst=True)
    application_status.drop(bind, checkfirst=True)
    user_role.drop(bind, checkfirst=True)
