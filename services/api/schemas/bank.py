import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from models.enums import LoanType


class BankBranding(BaseModel):
    primary_color: str
    logo_url: str


class LoanProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: LoanType
    interest_rate: Decimal
    min_amount: Decimal
    max_amount: Decimal
    min_term_months: int
    max_term_months: int


class BankOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    branding: BankBranding
    products: list[LoanProductOut]
