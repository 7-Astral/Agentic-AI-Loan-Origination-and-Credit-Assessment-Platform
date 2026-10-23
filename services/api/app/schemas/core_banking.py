import uuid

from pydantic import BaseModel


class SubmitApplicationRequest(BaseModel):
    bank_id: uuid.UUID
    applicant_id: uuid.UUID
    product_code: str
    requested_amount: float
    tenure_requested_months: int
    purpose: str | None = None
    external_reference: str | None = None
    applicant_legal_name: str | None = None
    assessment_tier: str | None = None
    assessment_score: float | None = None


class SubmitApplicationResponse(BaseModel):
    application_id: uuid.UUID
    status: str
    outcome: str
    pending_position_title: str | None = None
