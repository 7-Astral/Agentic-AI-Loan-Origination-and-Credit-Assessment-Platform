from datetime import datetime, timezone
from typing import Any

from app.agents.assessment.metric import Channel, Metric, MetricState

EXCLUDED_PURPOSES: set[str] = set() 


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _computed(value, channel: Channel, **kwargs) -> Metric:
    return Metric(value=value, state=MetricState.COMPUTED, channel=channel, computed_at=_now(), **kwargs)


def loan_purpose(filled: dict[str, Any]) -> Metric[str]:
    purpose = filled.get("loan_purpose")
    if purpose is None:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DECLARATION)

    return _computed(purpose, Channel.DECLARATION, inputs={
        "excluded": purpose in EXCLUDED_PURPOSES,
    })


def loan_amount_and_term(filled: dict[str, Any]) -> Metric[dict]:
    amount = filled.get("loan_amount")
    term = filled.get("loan_term_months")
    if amount is None or term is None:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DECLARATION)

    value = {"amount": amount, "term_months": term}
    return _computed(value, Channel.DECLARATION, unit="AUD / months")


def product_structure(product: dict) -> Metric[dict]:
    rate_type = product.get("rate_type")
    secured = product.get("secured")
    if rate_type is None or secured is None:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DECLARATION)

    value = {"rate_type": rate_type, "secured": secured}
    return _computed(value, Channel.DECLARATION)


def industry_sector_risk(filled: dict[str, Any], risk_table: dict) -> Metric[str]:
    employer_name = filled.get("employer_name")
    if employer_name is None:
        return Metric(value=None, state=MetricState.NOT_APPLICABLE, channel=Channel.POLICY)
    grade = risk_table.get("unclassified", "unclassified")
    return _computed(grade, Channel.POLICY, inputs={"employer_name": employer_name})


def assess_conditions(filled: dict[str, Any], product: dict, policy: dict) -> dict[str, Metric]:
    return {
        "loan_purpose": loan_purpose(filled),
        "loan_amount_and_term": loan_amount_and_term(filled),
        "product_structure": product_structure(product),
        "industry_sector_risk": industry_sector_risk(filled, policy.get("industry_risk", {})),
    }