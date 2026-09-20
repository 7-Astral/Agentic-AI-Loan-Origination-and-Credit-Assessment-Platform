import uuid

from pydantic import BaseModel


class SubmitApplicationRequest(BaseModel):
    """A completed chat-agent interview, handed off to the real pipeline."""

    bank_id: uuid.UUID
    applicant_id: uuid.UUID
    product_code: str
    requested_amount: float
    tenure_requested_months: int
    purpose: str | None = None
    # agent-backend's session_id — kept in the audit trail so a staff member
    # (or a developer) can trace an application back to its chat transcript.
    external_reference: str | None = None


class SubmitApplicationResponse(BaseModel):
    application_id: uuid.UUID
    status: str
    outcome: str
    pending_position_title: str | None = None
