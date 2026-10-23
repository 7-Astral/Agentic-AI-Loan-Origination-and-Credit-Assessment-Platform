from datetime import date as date_type, datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    JSON,
    MetaData,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    metadata = MetaData(schema="catalog")


class Bank(Base):
    __tablename__ = "banks"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    primary_color: Mapped[str] = mapped_column(String(20), default="#0f172a")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    integration_type: Mapped[str] = mapped_column(String(30), default="manual")
    adapter_config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LoanType(Base):
    __tablename__ = "loan_types"

    bank_id: Mapped[str] = mapped_column(ForeignKey("banks.id"), primary_key=True)
    code: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")

    categories: Mapped[list["Category"]] = relationship(back_populates="loan_type")


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        ForeignKeyConstraint(
            ["bank_id", "loan_type_code"],
            ["loan_types.bank_id", "loan_types.code"],
            name="fk_category_loan_type",
        ),
        UniqueConstraint("bank_id", "loan_type_code", "code", name="uq_category_per_loan_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bank_id: Mapped[str] = mapped_column(String(50))
    loan_type_code: Mapped[str] = mapped_column(String(30))
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(100), default="")

    loan_type: Mapped["LoanType"] = relationship(back_populates="categories")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        ForeignKeyConstraint(
            ["bank_id", "loan_type_code", "category_code"],
            ["categories.bank_id", "categories.loan_type_code", "categories.code"],
            name="fk_product_category_within_loan_type",
        ),
    )

    bank_id: Mapped[str] = mapped_column(ForeignKey("banks.id"), primary_key=True)
    product_code: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    loan_type_code: Mapped[str] = mapped_column(String(30))
    category_code: Mapped[str] = mapped_column(String(30))
    secured: Mapped[bool] = mapped_column(Boolean, default=False)
    min_amount: Mapped[int] = mapped_column(Integer)
    max_amount: Mapped[int] = mapped_column(Integer)
    min_term_months: Mapped[int] = mapped_column(Integer)
    max_term_months: Mapped[int] = mapped_column(Integer)
    interest_rate: Mapped[float] = mapped_column(Float)
    comparison_rate: Mapped[float] = mapped_column(Float)
    rate_type: Mapped[str] = mapped_column(String(20))
    establishment_fee: Mapped[int] = mapped_column(Integer)
    max_lvr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    features: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)


class DocumentType(Base):
    __tablename__ = "document_types"

    bank_id: Mapped[str] = mapped_column(ForeignKey("banks.id"), primary_key=True)
    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))


class DocumentRequirement(Base):
    __tablename__ = "document_requirements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["bank_id", "loan_type_code", "category_code"],
            ["categories.bank_id", "categories.loan_type_code", "categories.code"],
            name="fk_docreq_category_within_loan_type",
        ),
        ForeignKeyConstraint(
            ["bank_id", "document_type_code"],
            ["document_types.bank_id", "document_types.code"],
            name="fk_docreq_document_type",
        ),
        UniqueConstraint(
            "bank_id", "loan_type_code", "category_code", "document_type_code",
            name="uq_docreq_no_duplicates",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bank_id: Mapped[str] = mapped_column(String(50))
    loan_type_code: Mapped[str] = mapped_column(String(30))
    category_code: Mapped[str] = mapped_column(String(30))
    document_type_code: Mapped[str] = mapped_column(String(50))


class PolicySetting(Base):
    __tablename__ = "policy_settings"
    __table_args__ = (
        UniqueConstraint("bank_id", "key", "version", name="uq_policy_key_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bank_id: Mapped[str] = mapped_column(ForeignKey("banks.id"))
    key: Mapped[str] = mapped_column(String(50))
    version: Mapped[str] = mapped_column(String(20))
    document: Mapped[dict] = mapped_column(JSON)
    effective_from: Mapped[date_type] = mapped_column(Date)


class PolicyVersion(Base):
    __tablename__ = "policy_versions"
    __table_args__ = (
        UniqueConstraint("bank_id", "version", name="uq_policy_version_label"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bank_id: Mapped[str] = mapped_column(ForeignKey("banks.id"))
    version: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))  # "active" | "superseded"
    effective_from: Mapped[date_type] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str] = mapped_column(Text, default="")

    loan_policy_rows: Mapped[list["LoanPolicyRow"]] = relationship(
        back_populates="policy_version", cascade="all, delete-orphan"
    )


class LoanPolicyRow(Base):
    __tablename__ = "loan_policy_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_version_id: Mapped[int] = mapped_column(ForeignKey("policy_versions.id"))
    loan_type_code: Mapped[str] = mapped_column(String(30))
    category_code: Mapped[str] = mapped_column(String(30))
    min_age: Mapped[str] = mapped_column(Text, default="")
    residency_policy: Mapped[str] = mapped_column(Text, default="")
    deposit_lvr_policy: Mapped[str] = mapped_column(Text, default="")
    loan_amount_range: Mapped[str] = mapped_column(Text, default="")
    max_term: Mapped[str] = mapped_column(Text, default="")
    income_cash_flow_policy: Mapped[str] = mapped_column(Text, default="")
    serviceability_policy: Mapped[str] = mapped_column(Text, default="")
    credit_policy: Mapped[str] = mapped_column(Text, default="")

    policy_version: Mapped["PolicyVersion"] = relationship(back_populates="loan_policy_rows")


class Rule(Base):
    __tablename__ = "rules"
    __table_args__ = (
        UniqueConstraint("bank_id", "rule_id", name="uq_rule_id_per_bank"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bank_id: Mapped[str] = mapped_column(ForeignKey("banks.id"))
    rule_id: Mapped[str] = mapped_column(String(50))
    framework: Mapped[str] = mapped_column(String(20))
    document: Mapped[dict] = mapped_column(JSON)
