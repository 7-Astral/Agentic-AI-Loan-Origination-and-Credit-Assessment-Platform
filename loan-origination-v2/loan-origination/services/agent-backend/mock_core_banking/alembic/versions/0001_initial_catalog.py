from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "catalog"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "banks",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(60), nullable=False, unique=True),
        sa.Column("primary_color", sa.String(20), nullable=False, server_default="#0f172a"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("integration_type", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("adapter_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        schema=SCHEMA,
    )

    op.create_table(
        "loan_types",
        sa.Column("bank_id", sa.String(50), sa.ForeignKey(f"{SCHEMA}.banks.id"), primary_key=True),
        sa.Column("code", sa.String(30), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        schema=SCHEMA,
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("bank_id", sa.String(50), nullable=False),
        sa.Column("loan_type_code", sa.String(30), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(
            ["bank_id", "loan_type_code"],
            [f"{SCHEMA}.loan_types.bank_id", f"{SCHEMA}.loan_types.code"],
            name="fk_category_loan_type",
        ),
        sa.UniqueConstraint("bank_id", "loan_type_code", "code", name="uq_category_per_loan_type"),
        schema=SCHEMA,
    )

    op.create_table(
        "products",
        sa.Column("bank_id", sa.String(50), primary_key=True),
        sa.Column("product_code", sa.String(30), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("loan_type_code", sa.String(30), nullable=False),
        sa.Column("category_code", sa.String(30), nullable=False),
        sa.Column("secured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("min_amount", sa.Integer(), nullable=False),
        sa.Column("max_amount", sa.Integer(), nullable=False),
        sa.Column("min_term_months", sa.Integer(), nullable=False),
        sa.Column("max_term_months", sa.Integer(), nullable=False),
        sa.Column("interest_rate", sa.Float(), nullable=False),
        sa.Column("comparison_rate", sa.Float(), nullable=False),
        sa.Column("rate_type", sa.String(20), nullable=False),
        sa.Column("establishment_fee", sa.Integer(), nullable=False),
        sa.Column("max_lvr", sa.Integer(), nullable=True),
        sa.Column("features", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(
            ["bank_id", "loan_type_code", "category_code"],
            [f"{SCHEMA}.categories.bank_id", f"{SCHEMA}.categories.loan_type_code", f"{SCHEMA}.categories.code"],
            name="fk_product_category_within_loan_type",
        ),
        schema=SCHEMA,
    )

    op.create_table(
        "document_types",
        sa.Column("bank_id", sa.String(50), sa.ForeignKey(f"{SCHEMA}.banks.id"), primary_key=True),
        sa.Column("code", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "document_requirements",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("bank_id", sa.String(50), nullable=False),
        sa.Column("loan_type_code", sa.String(30), nullable=False),
        sa.Column("category_code", sa.String(30), nullable=False),
        sa.Column("document_type_code", sa.String(50), nullable=False),
        sa.ForeignKeyConstraint(
            ["bank_id", "loan_type_code", "category_code"],
            [f"{SCHEMA}.categories.bank_id", f"{SCHEMA}.categories.loan_type_code", f"{SCHEMA}.categories.code"],
            name="fk_docreq_category_within_loan_type",
        ),
        sa.ForeignKeyConstraint(
            ["bank_id", "document_type_code"],
            [f"{SCHEMA}.document_types.bank_id", f"{SCHEMA}.document_types.code"],
            name="fk_docreq_document_type",
        ),
        sa.UniqueConstraint(
            "bank_id", "loan_type_code", "category_code", "document_type_code",
            name="uq_docreq_no_duplicates",
        ),
        schema=SCHEMA,
    )

    op.create_table(
        "policy_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("bank_id", sa.String(50), sa.ForeignKey(f"{SCHEMA}.banks.id"), nullable=False),
        sa.Column("key", sa.String(50), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.UniqueConstraint("bank_id", "key", "version", name="uq_policy_key_version"),
        schema=SCHEMA,
    )

    op.create_table(
        "policy_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("bank_id", sa.String(50), sa.ForeignKey(f"{SCHEMA}.banks.id"), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.UniqueConstraint("bank_id", "version", name="uq_policy_version_label"),
        schema=SCHEMA,
    )

    op.create_table(
        "loan_policy_rows",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "policy_version_id",
            sa.Integer(),
            sa.ForeignKey(f"{SCHEMA}.policy_versions.id"),
            nullable=False,
        ),
        sa.Column("loan_type_code", sa.String(30), nullable=False),
        sa.Column("category_code", sa.String(30), nullable=False),
        sa.Column("min_age", sa.Text(), nullable=False, server_default=""),
        sa.Column("residency_policy", sa.Text(), nullable=False, server_default=""),
        sa.Column("deposit_lvr_policy", sa.Text(), nullable=False, server_default=""),
        sa.Column("loan_amount_range", sa.Text(), nullable=False, server_default=""),
        sa.Column("max_term", sa.Text(), nullable=False, server_default=""),
        sa.Column("income_cash_flow_policy", sa.Text(), nullable=False, server_default=""),
        sa.Column("serviceability_policy", sa.Text(), nullable=False, server_default=""),
        sa.Column("credit_policy", sa.Text(), nullable=False, server_default=""),
        schema=SCHEMA,
    )

    op.create_table(
        "rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("bank_id", sa.String(50), sa.ForeignKey(f"{SCHEMA}.banks.id"), nullable=False),
        sa.Column("rule_id", sa.String(50), nullable=False),
        sa.Column("framework", sa.String(20), nullable=False),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.UniqueConstraint("bank_id", "rule_id", name="uq_rule_id_per_bank"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("rules", schema=SCHEMA)
    op.drop_table("loan_policy_rows", schema=SCHEMA)
    op.drop_table("policy_versions", schema=SCHEMA)
    op.drop_table("policy_settings", schema=SCHEMA)
    op.drop_table("document_requirements", schema=SCHEMA)
    op.drop_table("document_types", schema=SCHEMA)
    op.drop_table("products", schema=SCHEMA)
    op.drop_table("categories", schema=SCHEMA)
    op.drop_table("loan_types", schema=SCHEMA)
    op.drop_table("banks", schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
