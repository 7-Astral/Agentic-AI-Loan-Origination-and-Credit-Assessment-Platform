from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

FiveCKey = Literal["character", "capacity", "capital", "collateral", "conditions"]

# bureau-verified / abn-verified: high confidence, from an external source of record.
# calculated: derived arithmetically from declared inputs (medium confidence).
# applicant-declared: taken as given from the applicant, unverified (medium or low).
# unavailable: the data needed wasn't present or the lookup wasn't possible (low, value null).
FiveCSource = Literal[
    "bureau-verified", "abn-verified", "applicant-declared", "calculated", "unavailable"
]
FiveCConfidence = Literal["high", "medium", "low"]
FieldRequirement = Literal["required", "confidence"]


class RequiredField(BaseModel):
    """One entry in a product's field checklist (see RequiredFieldTemplate)."""

    key: str
    five_c: FiveCKey
    requirement: FieldRequirement
    label: str


class MissingField(BaseModel):
    field: str
    label: str
    five_c: FiveCKey
    requirement: FieldRequirement


class FiveCField(BaseModel):
    value: Any | None = None
    source: FiveCSource
    confidence: FiveCConfidence
    notes: str | None = None


class FiveCs(BaseModel):
    character: FiveCField
    capacity: FiveCField
    capital: FiveCField
    collateral: FiveCField
    conditions: FiveCField


class CompletenessInfo(BaseModel):
    score: float
    missing_fields: list[MissingField]


class DataSourceEntry(BaseModel):
    source: str
    called: bool
    matched: bool | None = None
    reason: str | None = None


class RiskAssessmentRequest(BaseModel):
    """Accepts a raw or already-normalised application as a free-form JSON object — the
    normaliser tolerates missing fields and mixed formats, so no pre-validation is required
    here. `application_id` is echoed back if supplied, otherwise one is generated."""

    application_id: str | None = None
    application: dict[str, Any] = {}


class RiskAssessmentReport(BaseModel):
    application_id: str
    assessed_at: datetime
    completeness: CompletenessInfo
    five_cs: FiveCs
    data_sources: list[DataSourceEntry]
