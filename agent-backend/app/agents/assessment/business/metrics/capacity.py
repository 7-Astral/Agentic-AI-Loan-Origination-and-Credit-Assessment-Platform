from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.agents.assessment.metric import Channel, Metric, MetricState
from app.agents.assessment.retail.metrics.capacity import assessment_rate, proposed_repayment

CAPACITY_METRIC_NAMES = ["ebit", "ebitda", "total_debt_service", "dscr", "icr"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _computed(value, channel: Channel, **kwargs) -> Metric:
    return Metric(value=value, state=MetricState.COMPUTED, channel=channel, computed_at=_now(), **kwargs)


def _unavailable(channel: Channel = Channel.DECLARATION) -> Metric:
    return Metric(value=None, state=MetricState.UNAVAILABLE, channel=channel)


def _amount(filled: dict[str, Any], key: str) -> Decimal | None:
    value = filled.get(key)
    if value is None:
        return None
    return Decimal(str(value))


def ebit(filled: dict[str, Any]) -> Metric[Decimal]:
    net_profit = _amount(filled, "net_profit_before_tax")
    interest = _amount(filled, "interest_expense_annual")
    if net_profit is None or interest is None:
        return _unavailable()
    value = (net_profit + interest).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.DECLARATION, unit="AUD/year", inputs={
        "net_profit_before_tax": float(net_profit), "interest_expense_annual": float(interest),
    })


def ebitda(ebit_metric: Metric[Decimal], filled: dict[str, Any]) -> Metric[Decimal]:
    depreciation = _amount(filled, "depreciation_amortisation_annual")
    if not ebit_metric.usable or depreciation is None:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DERIVED)
    value = (ebit_metric.value + depreciation).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.DERIVED, unit="AUD/year", inputs={
        "ebit": float(ebit_metric.value), "depreciation_amortisation_annual": float(depreciation),
    })


def total_debt_service(filled: dict[str, Any], repayment: Metric[Decimal]) -> Metric[Decimal]:
    existing = _amount(filled, "existing_business_debt_repayments")
    if existing is None or not repayment.usable:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DERIVED)
    value = ((existing + repayment.value) * 12).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.DERIVED, unit="AUD/year", inputs={
        "existing_business_debt_repayments_monthly": float(existing),
        "proposed_repayment_monthly": float(repayment.value),
    })


def dscr(ebitda_metric: Metric[Decimal], debt_service: Metric[Decimal]) -> Metric[Decimal]:
    if not ebitda_metric.usable or not debt_service.usable or debt_service.value == 0:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DERIVED)
    value = (ebitda_metric.value / debt_service.value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.DERIVED, unit="ratio", inputs={
        "ebitda": float(ebitda_metric.value), "total_debt_service": float(debt_service.value),
    })


def icr(ebit_metric: Metric[Decimal], filled: dict[str, Any]) -> Metric[Decimal]:
    interest = _amount(filled, "interest_expense_annual")
    if not ebit_metric.usable or interest is None or interest == 0:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DERIVED)
    value = (ebit_metric.value / interest).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.DERIVED, unit="ratio", inputs={
        "ebit": float(ebit_metric.value), "interest_expense_annual": float(interest),
    })


def assess_capacity(filled: dict[str, Any], product: dict, policy: dict) -> dict[str, Metric]:
    rate = assessment_rate(product["interest_rate"], policy["assessment_rate_buffer"]["buffer_pct"])
    repayment = proposed_repayment(filled.get("loan_amount"), filled.get("loan_term_months"), rate)
    ebit_result = ebit(filled)
    ebitda_result = ebitda(ebit_result, filled)
    debt_service = total_debt_service(filled, repayment)

    return {
        "assessment_rate": rate,
        "proposed_repayment": repayment,
        "ebit": ebit_result,
        "ebitda": ebitda_result,
        "total_debt_service": debt_service,
        "dscr": dscr(ebitda_result, debt_service),
        "icr": icr(ebit_result, filled),
    }
