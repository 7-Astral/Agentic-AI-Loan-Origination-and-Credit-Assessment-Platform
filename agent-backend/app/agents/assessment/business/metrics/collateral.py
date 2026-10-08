from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.agents.assessment.metric import Channel, Metric, MetricState

COLLATERAL_METRIC_NAMES = ["security_value", "security_coverage_pct", "security_type_risk"]

SECURITY_TYPE_RISK = {
    "commercial_property": "low",
    "residential_property": "low",
    "business_assets": "medium",
    "equipment": "medium",
    "unsecured": "high",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _computed(value, channel: Channel, **kwargs) -> Metric:
    return Metric(value=value, state=MetricState.COMPUTED, channel=channel, computed_at=_now(), **kwargs)


def _unavailable(channel: Channel) -> Metric:
    return Metric(value=None, state=MetricState.UNAVAILABLE, channel=channel)


def _not_applicable(channel: Channel) -> Metric:
    return Metric(value=None, state=MetricState.NOT_APPLICABLE, channel=channel)


def security_value(filled: dict[str, Any]) -> Metric[Decimal]:
    if filled.get("security_offered") == "unsecured":
        return _not_applicable(Channel.DECLARATION)
    value = filled.get("security_value")
    if value is None:
        return _unavailable(Channel.DECLARATION)
    return _computed(Decimal(str(value)), Channel.DECLARATION, unit="AUD")


def security_coverage_pct(value_metric: Metric[Decimal], filled: dict[str, Any]) -> Metric[Decimal]:
    amount = filled.get("loan_amount")
    if not value_metric.usable or amount is None or Decimal(str(amount)) == 0:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DERIVED)
    pct = (value_metric.value / Decimal(str(amount)) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(pct, Channel.DERIVED, unit="%", inputs={
        "security_value": float(value_metric.value), "loan_amount": float(amount),
    })


def security_type_risk(filled: dict[str, Any]) -> Metric[str]:
    offered = filled.get("security_offered")
    if offered is None:
        return _unavailable(Channel.DECLARATION)
    return _computed(SECURITY_TYPE_RISK.get(offered, "medium"), Channel.DECLARATION, inputs={"security_offered": offered})


def assess_collateral(filled: dict[str, Any]) -> dict[str, Metric]:
    value_metric = security_value(filled)
    return {
        "security_value": value_metric,
        "security_coverage_pct": security_coverage_pct(value_metric, filled),
        "security_type_risk": security_type_risk(filled),
    }
