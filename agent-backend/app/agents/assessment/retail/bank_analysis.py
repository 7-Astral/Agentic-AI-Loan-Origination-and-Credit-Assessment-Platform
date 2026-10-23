from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.agents.assessment.metric import Channel, Metric, MetricState

EXPENSE_CATEGORIES = {
    "exp_food_groceries", "exp_clothing_personal_care", "exp_recreation_holidays",
    "exp_education_childcare", "exp_insurance", "exp_medical_health",
    "exp_rent_board", "exp_other_housing", "exp_phone_internet_media",
    "exp_vehicle_transport",
}

# Placeholder heuristic, not verified against real lending policy — same
# caution as every other figure in this project's config.
LUMP_SUM_THRESHOLD_PCT = Decimal("0.5")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _computed(value, channel: Channel, **kwargs) -> Metric:
    return Metric(value=value, state=MetricState.COMPUTED, channel=channel, computed_at=_now(), **kwargs)


def verified_expenses(transactions: list[dict[str, Any]] | None) -> Metric[Decimal]:
    if not transactions:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.OPEN_BANKING)

    debits = [t for t in transactions if t.get("direction") == "debit" and t.get("category") in EXPENSE_CATEGORIES]
    if not debits:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.OPEN_BANKING)

    by_category: dict[str, Decimal] = {}
    for t in debits:
        amt = Decimal(str(t["amount"]))
        by_category[t["category"]] = by_category.get(t["category"], Decimal("0")) + amt

    total = sum(by_category.values(), Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(total, Channel.OPEN_BANKING, unit="AUD/statement_period", inputs={
        k: float(v) for k, v in by_category.items()
    })


def genuine_savings(transactions: list[dict[str, Any]] | None) -> Metric[Decimal]:
    if not transactions:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.OPEN_BANKING)

    credits = [t for t in transactions if t.get("direction") == "credit" and t.get("category") != "transfer"]
    if not credits:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.OPEN_BANKING)

    total_credits = sum((Decimal(str(t["amount"])) for t in credits), Decimal("0"))
    if total_credits == 0:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.OPEN_BANKING)

    threshold = total_credits * LUMP_SUM_THRESHOLD_PCT
    genuine = [t for t in credits if Decimal(str(t["amount"])) <= threshold]
    excluded = [t for t in credits if Decimal(str(t["amount"])) > threshold]

    genuine_total = sum((Decimal(str(t["amount"])) for t in genuine), Decimal("0")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    excluded_total = sum((Decimal(str(t["amount"])) for t in excluded), Decimal("0"))

    return _computed(genuine_total, Channel.OPEN_BANKING, unit="AUD/statement_period", inputs={
        "total_credits": float(total_credits),
        "excluded_as_lump_sum": float(excluded_total),
        "excluded_count": len(excluded),
    })