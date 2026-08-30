from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, ForeignKeyConstraint, ARRAY, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class LoanType(Base):
    __tablename__ = "loan_types"

    code: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")

    categories: Mapped[list["Category"]] = relationship(back_populates="loan_type")


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("loan_type_code", "code", name="uq_category_per_loan_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_type_code: Mapped[str] = mapped_column(ForeignKey("loan_types.code"))
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(100), default="")

    loan_type: Mapped["LoanType"] = relationship(back_populates="categories")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        ForeignKeyConstraint(
            ["loan_type_code", "category_code"],
            ["categories.loan_type_code", "categories.code"],
            name="fk_product_category_within_loan_type",
        ),
    )

    product_code: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    loan_type_code: Mapped[str] = mapped_column(ForeignKey("loan_types.code"))
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

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))


class DocumentRequirement(Base):
    __tablename__ = "document_requirements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["loan_type_code", "category_code"],
            ["categories.loan_type_code", "categories.code"],
            name="fk_docreq_category_within_loan_type",
        ),
        UniqueConstraint(
            "loan_type_code", "category_code", "document_type_code",
            name="uq_docreq_no_duplicates",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_type_code: Mapped[str] = mapped_column(String(30))
    category_code: Mapped[str] = mapped_column(String(30))
    document_type_code: Mapped[str] = mapped_column(ForeignKey("document_types.code"))