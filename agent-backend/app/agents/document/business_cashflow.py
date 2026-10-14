from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from app.core import observability

DAYS_PER_MONTH = Decimal("30.4375")
MIN_PERIOD_DAYS = 28


def _date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _period_days(fields: dict[str, Any], transactions: list[dict]) -> int | None:
    start = _date(fields.get("statement_period_start"))
    end = _date(fields.get("statement_period_end"))
    if start is None or end is None:
        dates = [d for d in (_date(t.get("date")) for t in transactions) if d is not None]
        if not dates:
            return None
        start, end = min(dates), max(dates)
    days = (end - start).days + 1
    return days if days >= MIN_PERIOD_DAYS else None


def _total(transactions: list[dict], direction: str, category: str) -> Decimal:
    return sum(
        (abs(Decimal(str(t["amount"]))) for t in transactions
         if t.get("direction") == direction and t.get("category") == category and t.get("amount") is not None),
        Decimal("0"),
    )


def _money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


@observability.traced("document.business-cashflow")
def summarise_business_cashflow(fields: dict[str, Any]) -> dict[str, Any]:
    transactions = fields.get("transactions") or []
    if not transactions or not any(t.get("category") for t in transactions):
        return {}

    days = _period_days(fields, transactions)
    sales = _total(transactions, "credit", "sales_revenue")
    repayments = _total(transactions, "debit", "loan_repayment")
    summary: dict[str, Any] = {
        "cashflow_sales_receipts": _money(sales),
        "cashflow_ato_payments": _money(_total(transactions, "debit", "ato_payment")),
        "cashflow_dishonour_count": sum(1 for t in transactions if t.get("category") == "dishonour"),
        "cashflow_period_days": days,
    }
    if days is not None:
        months = Decimal(days) / DAYS_PER_MONTH
        summary["annualised_sales_receipts"] = _money(sales / months * 12)
        summary["monthly_loan_repayments"] = _money(repayments / months)
    return summary
