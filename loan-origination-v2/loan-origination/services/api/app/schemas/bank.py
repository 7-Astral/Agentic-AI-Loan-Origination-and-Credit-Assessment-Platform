import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class BankPositionOut(BaseModel):
    id: uuid.UUID
    bank_id: uuid.UUID
    title: str
    rank: int
    max_approval_amount: float | None
    can_manage_staff: bool
    can_manage_products: bool

    model_config = {"from_attributes": True}


class CreateBankStaffRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    position_id: uuid.UUID


class UpdateBankStaffRequest(BaseModel):
    """Partial update — only fields the client actually sent are applied
    (see the route's use of model_dump(exclude_unset=True)). Email and
    password aren't editable here; activation state is handled by the
    dedicated deactivate/reactivate routes, not this one."""

    full_name: str | None = None
    position_id: uuid.UUID | None = None


class CreateLoanProductRequest(BaseModel):
    product_type: str
    name: str
    min_amount: float
    max_amount: float
    interest_rate_min: float
    interest_rate_max: float
    tenure_min_months: int
    tenure_max_months: int


class UpdateLoanProductRequest(BaseModel):
    """Partial update — every field optional, only what's sent is applied.
    is_active is handled by the deactivate/reactivate routes instead, since
    products are never hard-deleted (they're referenced by past
    applications and by the chat agent's catalog)."""

    product_type: str | None = None
    name: str | None = None
    min_amount: float | None = None
    max_amount: float | None = None
    interest_rate_min: float | None = None
    interest_rate_max: float | None = None
    tenure_min_months: int | None = None
    tenure_max_months: int | None = None


class CreateLendingPolicyRequest(BaseModel):
    product_id: uuid.UUID | None = None
    auto_approval_max_amount: float
    min_credit_score: int
    max_dti_ratio: float


class UpdateLendingPolicyRequest(BaseModel):
    """Partial update — every field optional, only what's sent is applied.
    product_id may legitimately be set to null (bank-wide default), which
    exclude_unset=True still distinguishes from "not sent"."""

    product_id: uuid.UUID | None = None
    auto_approval_max_amount: float | None = None
    min_credit_score: int | None = None
    max_dti_ratio: float | None = None


class LoanApplicationOut(BaseModel):
    id: uuid.UUID
    applicant_id: uuid.UUID
    applicant_name: str | None = None
    applicant_email: str | None = None
    bank_id: uuid.UUID
    product_id: uuid.UUID
    loan_type: str
    requested_amount: float
    purpose: str | None
    status: str
    created_at: datetime
    pending_position_title: str | None = None
    chat_session_id: str | None = None

    model_config = {"from_attributes": True}


class ApplicationDecisionRequest(BaseModel):
    """A staff member's manual call on an escalated application — approve or
    reject. Distinct from the automatic route_loan_decision routing: this is
    always decision_type='manual', decided_by the acting staff member."""

    decision: str  # "approved" | "rejected"
    reason: str | None = None
    approved_amount: float | None = None


class ApplicationDecisionOut(BaseModel):
    application_id: uuid.UUID
    status: str
    decision: str
    decided_at: datetime


class LoanApplyRequest(BaseModel):
    bank_id: uuid.UUID
    product_id: uuid.UUID
    requested_amount: float
    purpose: str | None = None
    tenure_requested_months: int


class NotificationOut(BaseModel):
    id: uuid.UUID
    title: str
    message: str
    entity_type: str | None
    entity_id: str | None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
