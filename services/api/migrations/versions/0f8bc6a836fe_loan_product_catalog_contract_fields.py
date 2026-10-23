"""loan product catalog contract fields

Revision ID: 0f8bc6a836fe
Revises: e80fc8b39b2c
Create Date: 2026-09-11 08:58:05.227361

"""
from alembic import op
import sqlalchemy as sa
import app.db.types  # noqa: F401 — needed whenever a migration touches an EncryptedString column


# revision identifiers, used by Alembic.
revision = '0f8bc6a836fe'
down_revision = 'e80fc8b39b2c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("loan_products", sa.Column("product_code", sa.String(length=40), nullable=True))
    op.add_column(
        "loan_products", sa.Column("secured", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column(
        "loan_products",
        sa.Column("rate_type", sa.String(length=20), nullable=False, server_default="variable"),
    )
    op.add_column("loan_products", sa.Column("comparison_rate", sa.Numeric(5, 2), nullable=True))
    op.add_column(
        "loan_products",
        sa.Column("establishment_fee", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.add_column("loan_products", sa.Column("max_lvr", sa.Integer(), nullable=True))
    op.add_column(
        "loan_products",
        sa.Column(
            "features",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'::varchar[]"),
        ),
    )

    # Backfill a stable product_code for every existing product, then enforce
    # NOT NULL + uniqueness now that every row has one.
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, product_type FROM loan_products")).fetchall()
    for row in rows:
        code = f"{row.product_type.upper()}-{str(row.id).split('-')[0].upper()}"
        conn.execute(
            sa.text("UPDATE loan_products SET product_code = :code WHERE id = :id"),
            {"code": code, "id": row.id},
        )

    op.alter_column("loan_products", "product_code", nullable=False)
    op.create_unique_constraint("uq_loan_products_product_code", "loan_products", ["product_code"])

    # Drop server defaults now that the backfill is done — new rows should
    # get their values from the application layer (model defaults), not a
    # frozen DB default.
    op.alter_column("loan_products", "secured", server_default=None)
    op.alter_column("loan_products", "rate_type", server_default=None)
    op.alter_column("loan_products", "establishment_fee", server_default=None)
    op.alter_column("loan_products", "features", server_default=None)


def downgrade() -> None:
    op.drop_constraint("uq_loan_products_product_code", "loan_products", type_="unique")
    op.drop_column("loan_products", "features")
    op.drop_column("loan_products", "max_lvr")
    op.drop_column("loan_products", "establishment_fee")
    op.drop_column("loan_products", "comparison_rate")
    op.drop_column("loan_products", "rate_type")
    op.drop_column("loan_products", "secured")
    op.drop_column("loan_products", "product_code")
