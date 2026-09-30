from decimal import ROUND_HALF_UP, Decimal
from typing import Any

PERIODS_PER_YEAR = {
    "weekly": 52,
    "fortnightly": 26,
    "monthly": 12,
    "quarterly": 4,
    "annually": 1,
}

_ALIASES = {
    "week": "weekly", "per week": "weekly", "a week": "weekly",
    "fortnight": "fortnightly", "biweekly": "fortnightly", "bi-weekly": "fortnightly",
    "month": "monthly", "per month": "monthly", "a month": "monthly",
    "quarter": "quarterly",
    "year": "annually", "yearly": "annually", "annual": "annually", "per year": "annually", "a year": "annually",
}


def normalise_frequency(frequency: Any) -> str | None:
    if not isinstance(frequency, str):
        return None
    key = frequency.strip().lower()
    key = _ALIASES.get(key, key)
    return key if key in PERIODS_PER_YEAR else None


def to_monthly(amount: Any, frequency: Any) -> Decimal:
    value = Decimal(str(amount))
    freq = normalise_frequency(frequency) or "monthly"
    monthly = value * PERIODS_PER_YEAR[freq] / 12
    return monthly.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def to_annual(amount: Any, frequency: Any) -> Decimal:
    value = Decimal(str(amount))
    freq = normalise_frequency(frequency) or "annually"
    return (value * PERIODS_PER_YEAR[freq]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def convert(amount: Any, from_frequency: str, to_frequency: str) -> Decimal:
    value = Decimal(str(amount)) * PERIODS_PER_YEAR[from_frequency] / PERIODS_PER_YEAR[to_frequency]
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def read_stated_amount(raw: Any) -> tuple[Any, str | None]:
    if isinstance(raw, dict):
        return raw.get("amount"), normalise_frequency(raw.get("frequency"))
    return raw, None
