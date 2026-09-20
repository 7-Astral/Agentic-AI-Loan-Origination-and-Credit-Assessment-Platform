from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.agents.assessment.metric import Channel, Metric, MetricState

CHARACTER_METRIC_NAMES = [
    "credit_score",
    "worst_rhi_6mo",
    "worst_rhi_24mo",
    "missed_payment_count_24mo",
    "unpaid_defaults",
    "paid_defaults",
    "enquiry_velocity_6mo",
    "bankruptcy_judgment_status",
    "hardship_flags_12mo",
    "undisclosed_liabilities",
]

CARD_LIMIT_SERVICING_RATE = Decimal("0.03")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _computed(value, **kwargs) -> Metric:
    return Metric(value=value, state=MetricState.COMPUTED, channel=Channel.BUREAU, computed_at=_now(), **kwargs)


def _unavailable(**kwargs) -> Metric:
    return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.BUREAU, **kwargs)


def _as_of(report: dict) -> date:
    return datetime.fromisoformat(report["generated_at"]).date()


def _within(as_of: date, when: str, months: int) -> bool:
    return date.fromisoformat(when) >= as_of - timedelta(days=round(30.4375 * months))


def _histories(report: dict, months: int) -> list[list[int]]:
    return [a["rhi"][:months] for a in report["accounts"] if a.get("rhi")]


def credit_score(report: dict) -> Metric[int]:
    score = report["score"]
    return _computed(score["value"], unit=f"score ({score['scale_min']}-{score['scale_max']})",
                     inputs={"band": score["band"], "report_id": report["report_id"]})


def worst_rhi(report: dict, months: int) -> Metric[int]:
    histories = _histories(report, months)
    if not histories:
        return _unavailable(inputs={"reason": "no_repayment_history"})
    return _computed(max(max(h) for h in histories), unit="rhi (0-3)", inputs={"window_months": months})


def missed_payment_count(report: dict, months: int) -> Metric[int]:
    histories = _histories(report, months)
    if not histories:
        return _unavailable(inputs={"reason": "no_repayment_history"})
    return _computed(sum(1 for h in histories for code in h if code >= 1), unit="months",
                     inputs={"window_months": months})


def defaults(report: dict, status: str) -> Metric[int]:
    matching = [d for d in report["defaults"] if d["status"] == status]
    return _computed(len(matching), unit="count", inputs={"total_amount": sum(d["amount"] for d in matching)})


def enquiry_velocity(report: dict, months: int) -> Metric[int]:
    as_of = _as_of(report)
    recent = [e for e in report["enquiries"] if _within(as_of, e["date"], months)]
    return _computed(len(recent), unit="count", inputs={"window_months": months})


def bankruptcy_judgment_status(report: dict) -> Metric[str]:
    insolvency = report.get("insolvency")
    if insolvency:
        status = insolvency["type"]
    elif any(j["status"] == "unsatisfied" for j in report["judgments"]):
        status = "judgment"
    else:
        status = "none"
    return _computed(status, inputs={"judgment_count": len(report["judgments"])})


def hardship_flags(report: dict, months: int) -> Metric[int]:
    as_of = _as_of(report)
    recent = [h for h in report["hardship"] if _within(as_of, h["date"], months)]
    return _computed(len(recent), unit="count", inputs={"window_months": months})


def undisclosed_liabilities(report: dict, filled: dict[str, Any]) -> Metric[Decimal]:
    declared_loans = filled.get("other_loan_repayments_monthly")
    declared_limit = filled.get("credit_card_limit_total")
    if declared_loans is None and declared_limit is None:
        return _unavailable(inputs={"reason": "nothing_declared_to_compare"})

    open_accounts = [a for a in report["accounts"] if a["status"] == "open"]
    bureau_repayments = Decimal(str(sum(a["monthly_repayment"] for a in open_accounts if a["type"] != "credit_card")))
    bureau_limits = Decimal(str(sum(a["limit"] for a in open_accounts if a["type"] == "credit_card")))

    declared_repayments = Decimal(str(declared_loans or 0)) + Decimal(str(filled.get("mortgage_repayment_monthly") or 0))
    declared_limits = Decimal(str(declared_limit or 0))

    repayment_gap = max(Decimal("0"), bureau_repayments - declared_repayments)
    limit_gap = max(Decimal("0"), bureau_limits - declared_limits)
    value = (repayment_gap + limit_gap * CARD_LIMIT_SERVICING_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(value, unit="AUD/month", inputs={
        "bureau_repayments_monthly": float(bureau_repayments), "declared_repayments_monthly": float(declared_repayments),
        "bureau_card_limits": float(bureau_limits), "declared_card_limits": float(declared_limits),
    })


def assess_character(filled: dict[str, Any], bureau_report: dict | None = None) -> dict[str, Metric]:
    if bureau_report is None:
        return {name: _unavailable() for name in CHARACTER_METRIC_NAMES}

    return {
        "credit_score": credit_score(bureau_report),
        "worst_rhi_6mo": worst_rhi(bureau_report, 6),
        "worst_rhi_24mo": worst_rhi(bureau_report, 24),
        "missed_payment_count_24mo": missed_payment_count(bureau_report, 24),
        "unpaid_defaults": defaults(bureau_report, "unpaid"),
        "paid_defaults": defaults(bureau_report, "paid"),
        "enquiry_velocity_6mo": enquiry_velocity(bureau_report, 6),
        "bankruptcy_judgment_status": bankruptcy_judgment_status(bureau_report),
        "hardship_flags_12mo": hardship_flags(bureau_report, 12),
        "undisclosed_liabilities": undisclosed_liabilities(bureau_report, filled),
    }
