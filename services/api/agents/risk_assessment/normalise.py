from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from agents.questions.validation import parse_number
from schemas.application import (
    Applicant,
    BnplAccount,
    Business,
    Collateral,
    CreditCard,
    Employment,
    ExistingDebt,
    ExistingLoan,
    Loan,
    NormalizedApplication,
)

# Tried in order; DD/MM/YYYY is preferred over MM/DD/YYYY (Australian context) — the
# ambiguous US-style form is only tried last, as a fallback.
_DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d %B %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%B %d %Y",
    "%m/%d/%Y",
]


def _coerce_str(raw: Any) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        stripped = raw.strip()
        return stripped or None
    return str(raw).strip() or None


def _coerce_decimal(raw: Any) -> Decimal | None:
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float, Decimal)):
        try:
            return Decimal(str(raw))
        except InvalidOperation:
            return None
    if isinstance(raw, str):
        return parse_number(raw)
    return None


def _coerce_int(raw: Any) -> int | None:
    value = _coerce_decimal(raw)
    return int(value) if value is not None else None


def _coerce_bool(raw: Any) -> bool | None:
    """Distinct from agents.questions.validation.parse_boolean, which is for free-text chat
    replies — this handles native JSON booleans and stringy "true"/"false"/"yes"/"no" from
    direct API callers of /risk-assessment."""
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        text = raw.strip().lower()
        if text in ("true", "yes", "1"):
            return True
        if text in ("false", "no", "0"):
            return False
    return None


def _coerce_float(raw: Any) -> float | None:
    value = _coerce_decimal(raw)
    return float(value) if value is not None else None


def _coerce_date(raw: Any) -> date | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _dict_at(source: Any, key: str) -> dict[str, Any]:
    value = source.get(key) if isinstance(source, dict) else None
    return value if isinstance(value, dict) else {}


def _list_at(source: Any, key: str) -> list[Any]:
    value = source.get(key) if isinstance(source, dict) else None
    return value if isinstance(value, list) else []


def _normalise_employment(raw: dict[str, Any]) -> Employment:
    return Employment(
        status=_coerce_str(raw.get("status")),
        employer=_coerce_str(raw.get("employer")),
        years_in_role=_coerce_float(raw.get("years_in_role")),
        income=_coerce_decimal(raw.get("income")),
        income_frequency=_coerce_str(raw.get("income_frequency")),
    )


def _normalise_applicant(raw: dict[str, Any]) -> Applicant:
    return Applicant(
        name=_coerce_str(raw.get("name")),
        dob=_coerce_date(raw.get("dob")),
        address=_coerce_str(raw.get("address")),
        employment=_normalise_employment(_dict_at(raw, "employment")),
        monthly_expenses=_coerce_decimal(raw.get("monthly_expenses")),
    )


def _normalise_loan(raw: dict[str, Any]) -> Loan:
    return Loan(
        amount=_coerce_decimal(raw.get("amount")),
        purpose=_coerce_str(raw.get("purpose")),
        term_months=_coerce_int(raw.get("term_months")),
        product_type=_coerce_str(raw.get("product_type")),
        interest_only=_coerce_bool(raw.get("interest_only")),
        balloon_payment=_coerce_decimal(raw.get("balloon_payment")),
    )


def _normalise_existing_debt(raw: dict[str, Any]) -> ExistingDebt:
    loans = [
        ExistingLoan(
            type=_coerce_str(item.get("type")),
            balance=_coerce_decimal(item.get("balance")),
            monthly_repayment=_coerce_decimal(item.get("monthly_repayment")),
        )
        for item in _list_at(raw, "loans")
        if isinstance(item, dict)
    ]
    bnpl_accounts = [
        BnplAccount(
            provider=_coerce_str(item.get("provider")),
            limit=_coerce_decimal(item.get("limit")),
            balance=_coerce_decimal(item.get("balance")),
        )
        for item in _list_at(raw, "bnpl_accounts")
        if isinstance(item, dict)
    ]
    credit_cards = [
        CreditCard(
            limit=_coerce_decimal(item.get("limit")),
            balance=_coerce_decimal(item.get("balance")),
        )
        for item in _list_at(raw, "credit_cards")
        if isinstance(item, dict)
    ]
    return ExistingDebt(loans=loans, bnpl_accounts=bnpl_accounts, credit_cards=credit_cards)


def _normalise_business(raw: dict[str, Any]) -> Business:
    return Business(
        abn=_coerce_str(raw.get("abn")),
        entity_name=_coerce_str(raw.get("entity_name")),
        industry=_coerce_str(raw.get("industry")),
        years_trading=_coerce_float(raw.get("years_trading")),
        annual_turnover=_coerce_decimal(raw.get("annual_turnover")),
        net_profit=_coerce_decimal(raw.get("net_profit")),
        employee_count=_coerce_int(raw.get("employee_count")),
    )


def _normalise_collateral(raw: dict[str, Any]) -> Collateral:
    return Collateral(
        asset_type=_coerce_str(raw.get("asset_type")),
        estimated_value=_coerce_decimal(raw.get("estimated_value")),
        deposit_amount=_coerce_decimal(raw.get("deposit_amount")),
    )


def normalise_application(raw: Any) -> NormalizedApplication:
    """Coerces a raw, possibly-incomplete application payload into the canonical schema.
    Every field is optional at every level — this never raises on missing data, malformed
    dates/currency strings, or unexpected shapes; it just leaves the affected field `None`
    (or an empty list) for `missing_fields`/the assessment downstream to account for."""
    source = raw if isinstance(raw, dict) else {}

    return NormalizedApplication(
        applicant=_normalise_applicant(_dict_at(source, "applicant")),
        loan=_normalise_loan(_dict_at(source, "loan")),
        existing_debt=_normalise_existing_debt(_dict_at(source, "existing_debt")),
        business=_normalise_business(_dict_at(source, "business")),
        collateral=_normalise_collateral(_dict_at(source, "collateral")),
    )
