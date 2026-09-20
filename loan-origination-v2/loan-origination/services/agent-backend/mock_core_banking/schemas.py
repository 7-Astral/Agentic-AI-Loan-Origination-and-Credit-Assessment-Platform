from datetime import date, datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)



class BankOut(CamelModel):
    id: str
    name: str
    slug: str
    primary_color: str
    status: str
    created_at: datetime


class BankCreate(CamelModel):
    name: str
    primary_color: str = "#0f172a"
    status: str = "draft"


class BankUpdate(CamelModel):
    name: str
    primary_color: str
    status: str


class CategoryOut(CamelModel):
    code: str
    name: str


class CategoryCreate(CamelModel):
    code: str
    name: str


class CategoryRename(CamelModel):
    name: str


class LoanTypeOut(CamelModel):
    code: str
    name: str
    description: str
    categories: list[CategoryOut] = []


class LoanTypeCreate(CamelModel):
    code: str
    name: str
    description: str = ""


class LoanTypeUpdate(CamelModel):
    name: str
    description: str


class ProductOut(CamelModel):
    product_code: str
    name: str
    loan_type_code: str
    category_code: str
    secured: bool
    min_amount: int
    max_amount: int
    min_term_months: int
    max_term_months: int
    interest_rate: float
    comparison_rate: float
    rate_type: str
    establishment_fee: int
    max_lvr: int | None
    features: list[str]


class ProductCreate(CamelModel):
    product_code: str
    name: str
    loan_type_code: str
    category_code: str
    secured: bool = False
    min_amount: int
    max_amount: int
    min_term_months: int
    max_term_months: int
    interest_rate: float
    comparison_rate: float
    rate_type: str
    establishment_fee: int
    max_lvr: int | None = None
    features: list[str] = []


class ProductUpdate(ProductCreate):
    pass


class DocumentTypeOut(CamelModel):
    code: str
    name: str


class DocumentTypeCreate(CamelModel):
    code: str
    name: str


class DocumentRequirementOut(CamelModel):
    loan_type_code: str
    category_code: str
    document_type_code: str


class DocumentRequirementToggle(CamelModel):
    document_type_code: str
    loan_type_code: str
    category_code: str


class LoanPolicyRowIn(CamelModel):
    loan_type_code: str
    category_code: str
    min_age: str = ""
    residency_policy: str = ""
    deposit_lvr_policy: str = ""
    loan_amount_range: str = ""
    max_term: str = ""
    income_cash_flow_policy: str = ""
    serviceability_policy: str = ""
    credit_policy: str = ""


class LoanPolicyRowOut(LoanPolicyRowIn):
    pass


class PolicyVersionOut(CamelModel):
    id: str
    version: str
    status: str
    effective_from: date
    created_at: datetime
    notes: str
    loan_policy_rows: list[LoanPolicyRowOut]


class PolicyVersionCreate(CamelModel):
    version: str
    effective_from: date
    notes: str = ""
    loan_policy_rows: list[LoanPolicyRowIn] = []

class RuleOut(CamelModel):
    rule_id: str
    framework: str
    requires: list[str]
    when: str
    status: str
    message: str


class RuleCreate(CamelModel):
    rule_id: str
    framework: str
    requires: list[str] = []
    when: str
    status: str
    message: str


class RuleUpdate(RuleCreate):
    pass
