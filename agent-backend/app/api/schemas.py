from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StartRequest(BaseModel):
    product_code: str | None = None

    bank_id: str | None = None


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
    products: list[ProductOption] | None = None
    note: str | None = None


class ChatMessageOut(BaseModel):
    role: str
    content: str


class ResumeResponse(TurnResponse):

    messages: list[ChatMessageOut] = []
    submitted: bool = False


class InfoRequestCreate(BaseModel):
    kind: str = Field(pattern="^(information|document)$")
    message: str = Field(min_length=1, max_length=2000)
    document_code: str | None = Field(default=None, max_length=50)
    requested_by: str | None = Field(default=None, max_length=150)


class InfoRequestReply(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class InfoRequestOut(BaseModel):
    id: str
    kind: str
    message: str
    document_code: str | None = None
    document_name: str | None = None
    requested_by: str | None = None
    status: str
    response_text: str | None = None
    document_id: str | None = None
    created_at: datetime
    answered_at: datetime | None = None


class OpenInfoRequestsOut(BaseModel):
    session_id: str
    product_code: str | None = None
    open_count: int
    latest_message: str


class DecisionRequest(BaseModel):
    outcome: str = Field(pattern="^(approved|declined|refer_to_underwriter|withdrawn)$")
    reasoning: str = ""


class DecisionResponse(BaseModel):
    session_id: str
    outcome: str
    reasoning: str
    status: str


class ScoredMetricOut(BaseModel):
    metric: str
    raw_value: Any = None
    unit: str | None = None
    channel: str | None = None
    normalized_score: float


class SkippedMetricOut(BaseModel):
    metric: str
    reason: str


class GroupScoreOut(BaseModel):
    score: float | None
    state: str
    metrics_used: list[ScoredMetricOut] = []
    metrics_skipped: list[SkippedMetricOut] = []


class ConditionOut(BaseModel):
    id: str
    category: str
    text: str
    reason: str
    blocking: bool


class RuleResultOut(BaseModel):
    rule_id: str
    status: str
    message: str | None = None
    missing: list[str] | None = None
    detail: str | None = None
    inputs: dict[str, Any] | None = None


class RuleBasedIndicatorOut(BaseModel):
    tier: str
    fail_count: int
    flag_count: int
    provisional_count: int


class ApplicantFactOut(BaseModel):
    id: str
    label: str
    value: Any


class KeyFigureOut(BaseModel):
    metric: str
    label: str
    value: Any
    unit: str | None = None


class PolicyComparisonOut(BaseModel):
    metric: str
    label: str
    value: Any
    unit: str | None = None
    threshold: Any
    threshold_label: str
    meets_threshold: bool


class DocumentSummaryOut(BaseModel):
    document_id: str
    verification_type: str
    original_filename: str
    status: str
    uploaded_at: datetime
    extracted: bool


class VerificationOut(BaseModel):
    slot_id: str
    declared_value: str
    extracted_value: str
    status: str
    checked_at: datetime


class TranscriptMessageOut(BaseModel):
    role: str
    content: str
    turn: int | None = None
    created_at: datetime


class RiskFactorOut(BaseModel):
    severity: str
    label: str
    detail: str


class RiskProfileOut(BaseModel):
    category: str
    factors: list[RiskFactorOut] = []


class ApplicationReportOut(BaseModel):
    session_id: str
    bank_id: str
    product_code: str
    product_name: str | None = None
    status: str
    generated_at: datetime
    group_scores: dict[str, GroupScoreOut]
    overall_score: float | None
    weights_applied: dict[str, float]
    score_bands_applied: dict[str, float]
    tier: str
    data_completeness: dict[str, str]
    conditions_of_approval: list[ConditionOut]
    rule_results: list[RuleResultOut]
    rule_based_indicator: RuleBasedIndicatorOut
    metrics_computed: int
    metrics_total: int
    narrative_summary: str | None = None
    risk_profile: RiskProfileOut
    applicant_summary: list[ApplicantFactOut] = []
    key_figures: list[KeyFigureOut] = []
    policy_comparison: list[PolicyComparisonOut] = []
    documents: list[DocumentSummaryOut] = []
    verifications: list[VerificationOut] = []
    transcript: list[TranscriptMessageOut] = []


class ApplicationSummaryOut(BaseModel):
    session_id: str
    product_code: str | None
    status: str
    overall_score: float | None
    tier: str | None
    created_at: datetime


class ApplicationListOut(BaseModel):
    applications: list[ApplicationSummaryOut]
    total: int