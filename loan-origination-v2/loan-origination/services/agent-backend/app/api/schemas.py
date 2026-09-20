from typing import Any

from pydantic import BaseModel, Field


class StartRequest(BaseModel):
    product_code: str | None = None
    # bank whose catalog this session should use — falls back to
    # settings.platform_bank_id when the caller doesn't specify one
    bank_id: str | None = None
    # product_code: str = Field(default="VL-NEW-020")


class SlotHint(BaseModel):
    id: str
    label: str
    type: str
    options: list[str] | None = None


class Progress(BaseModel):
    answered: int
    remaining_known: int
    current_phase: int | None
    complete: bool


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ProductOption(BaseModel):
    """One product on offer during the discovery stage's product_selection
    turn — the same fields discovery.py's _product_brief pulls off the
    catalog. Sent alongside `question` so the frontend can render each
    option as its own card instead of parsing them back out of chat text."""

    product_code: str
    name: str
    interest_rate: float | None = None
    comparison_rate: float | None = None
    rate_type: str | None = None
    min_amount: float
    max_amount: float
    min_term_months: int
    max_term_months: int
    features: list[str] = []


class ApplicationResponse(BaseModel):
    session_id: str
    product_code: str
    schema_version: str
    progress: Progress
    filled: dict[str, Any]
    provenance: dict[str, dict]
    transcript: list[dict]

class TurnResponse(BaseModel):
    session_id: str
    stage: str
    question: str | None
    slots_in_play: list[SlotHint] = []
    progress: Progress | None = None
    complete: bool
    escalated: bool = False
    product_code: str | None = None
    # Populated only on a discovery "product_selection" turn — the products
    # the applicant is choosing between, for the frontend to render as cards.
    products: list[ProductOption] | None = None


class DecisionRequest(BaseModel):
    outcome: str = Field(pattern="^(approved|declined|refer_to_underwriter|withdrawn)$")
    reasoning: str = ""


class DecisionResponse(BaseModel):
    session_id: str
    outcome: str
    reasoning: str
    status: str