import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from models.enums import ApplicationStatus, OfficerActionType
from schemas.customer_profile import CustomerProfileOut
from schemas.risk_assessment import RiskAssessmentReport

# The *persisted* loan application record (status, officer actions, etc.) — unrelated to
# schemas/application.py's NormalizedApplication, which is the risk-assessment domain's
# transient input shape and is never itself stored. Split into its own file to avoid the
# name clash; see models/application.py for the same note on the ORM side.

Outcome = Literal["approved", "rejected", "overridden", "info_requested"]


class ApplicationSummary(BaseModel):
    id: uuid.UUID
    bank_id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str
    product_id: uuid.UUID
    product_name: str
    status: ApplicationStatus
    loan_amount: Decimal
    loan_term_months: int
    purpose: str | None
    created_at: datetime
    updated_at: datetime


class OfficerActionOut(BaseModel):
    """Officer-facing only — never included in a customer's view of an application. See
    routers/applications.py's `_build_customer_view` vs `_build_officer_view`."""

    id: uuid.UUID
    officer_id: uuid.UUID
    officer_name: str
    action: OfficerActionType
    reason: str | None
    created_at: datetime


class ApplicationDetail(ApplicationSummary):
    # Customer view: derived, never the raw action log. Only one of outcome /
    # info_request_message is ever populated (status == decided vs not).
    outcome: Outcome | None = None
    info_request_message: str | None = None
    # Officer view only — always empty/omitted for a customer response, never just
    # hidden client-side.
    actions: list[OfficerActionOut] = []
    customer_profile: CustomerProfileOut | None = None
    risk_report: RiskAssessmentReport | None = None


class ApplicationActionRequest(BaseModel):
    action: OfficerActionType
    reason: str | None = None
