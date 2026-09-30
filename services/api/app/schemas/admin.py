import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class BankOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    contact_email: str | None
    status: str

    model_config = {"from_attributes": True}


class LoanProductOut(BaseModel):
    id: uuid.UUID
    bank_id: uuid.UUID
    product_code: str | None
    product_type: str
    name: str
    min_amount: float
    max_amount: float
    interest_rate_min: float
    interest_rate_max: float
    tenure_min_months: int
    tenure_max_months: int
    is_active: bool

    model_config = {"from_attributes": True}


class LendingPolicyOut(BaseModel):
    id: uuid.UUID
    bank_id: uuid.UUID
    product_id: uuid.UUID | None
    auto_approval_max_amount: float
    min_credit_score: int
    max_dti_ratio: float
    is_active: bool

    model_config = {"from_attributes": True}


class AuditLogOut(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: str
    entity_label: str | None = None
    action: str
    performed_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    total_users: int
    total_banks: int
    total_loan_products: int
    total_applications: int


class CreateStaffRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    bank_id: uuid.UUID
    position_id: uuid.UUID | None = None


class CreateBankRequest(BaseModel):
    name: str
    code: str
    contact_email: EmailStr | None = None


class CreateBankPositionRequest(BaseModel):
    """One rung on a bank's approval ladder. max_approval_amount left unset
    means unlimited authority. can_manage_staff/can_manage_products are what
    make a position a "branch manager" in practice — there's no separate
    per-bank admin role, a staff account with a position that has both of
    these set to true is how a bank gets its own local admin."""

    title: str
    rank: int
    max_approval_amount: float | None = None
    can_manage_staff: bool = False
    can_manage_products: bool = False
