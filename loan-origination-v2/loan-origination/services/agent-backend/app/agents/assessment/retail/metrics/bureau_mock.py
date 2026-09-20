"""Mock credit-score estimate — NOT a real bureau pull.

This platform has no bureau integration (see character.py's docstring, and
the capstone's db-schema-design.md §8.4/E — services/api's
credit_assessments table stays unpopulated). Rather than leave the
character assessment's credit_score metric permanently blank, this derives
a synthetic 300-850 estimate from data the Five C's engine already computed
for this application (debt-to-income ratio, net-surplus ratio) plus the
applicant's declared employment status — a transparent, explainable stand-in
so the report has something concrete for staff to see, not a real score.

Tagged as DERIVED (not BUREAU) and its unit string says "mock estimate" so
nothing downstream can mistake it for a genuine bureau pull.
"""

from decimal import Decimal
from typing import Any

from app.agents.assessment.metric import Channel, Metric, MetricState

BASE_SCORE = 650
MIN_SCORE = 300
MAX_SCORE = 850

EMPLOYMENT_ADJUSTMENTS = {
    "permanent_full_time": 40,
    "permanent_part_time": 10,
    "self_employed": 10,
    "casual": -20,
    "contract": -20,
    "unemployed": -100,
}


def _dti_adjustment(dti: Decimal) -> int:
    """Debt-to-income ratio — lower is better."""
    if dti <= Decimal("0.20"):
        return 80
    if dti <= Decimal("0.35"):
        return 40
    if dti <= Decimal("0.45"):
        return 0
    if dti <= Decimal("0.55"):
        return -60
    return -120


def _nsr_adjustment(nsr: Decimal) -> int:
    """Net surplus ratio (surplus / repayment) — higher is better."""
    if nsr >= Decimal("2.0"):
        return 60
    if nsr >= Decimal("1.5"):
        return 30
    if nsr >= Decimal("1.0"):
        return 0
    if nsr >= Decimal("0.5"):
        return -60
    return -150


def mock_credit_score(capacity_metrics: dict[str, Metric], filled: dict[str, Any]) -> Metric:
    dti_metric = capacity_metrics.get("dti")
    nsr_metric = capacity_metrics.get("nsr")
    dti_usable = dti_metric is not None and dti_metric.usable
    nsr_usable = nsr_metric is not None and nsr_metric.usable

    if not dti_usable and not nsr_usable:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DERIVED)

    score = BASE_SCORE
    inputs: dict[str, Any] = {}

    if dti_usable:
        adjustment = _dti_adjustment(dti_metric.value)
        score += adjustment
        inputs["dti"] = float(dti_metric.value)
        inputs["dti_adjustment"] = adjustment

    if nsr_usable:
        adjustment = _nsr_adjustment(nsr_metric.value)
        score += adjustment
        inputs["nsr"] = float(nsr_metric.value)
        inputs["nsr_adjustment"] = adjustment

    employment_status = filled.get("employment_status")
    employment_adjustment = EMPLOYMENT_ADJUSTMENTS.get(employment_status, 0) if employment_status else 0
    if employment_adjustment:
        inputs["employment_status"] = employment_status
        inputs["employment_adjustment"] = employment_adjustment
    score += employment_adjustment

    score = max(MIN_SCORE, min(MAX_SCORE, score))

    return Metric(
        value=score,
        state=MetricState.COMPUTED,
        channel=Channel.DERIVED,
        unit="mock estimate (300-850) — no bureau integration",
        inputs=inputs,
    )
