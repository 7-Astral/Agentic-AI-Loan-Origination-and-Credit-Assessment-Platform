import re
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.policy.loader import DATA_STATUS, SOURCE
from app.core.config import get_settings
from app.models.policy import PolicyChunk

CATEGORY_ORDER = [
    ("Min Age", "Minimum age"),
    ("Residency Policy", "Residency"),
    ("Dummy Loan Amount", "Loan amount"),
    ("Dummy Max Term", "Loan term"),
    ("Deposit / LVR Policy", "Deposit / LVR"),
    ("Income / Cash Flow Policy", "Income"),
    ("Serviceability Policy", "Serviceability"),
    ("Credit Policy", "Credit history"),
]

ACCEPTED_RESIDENCY = {"citizen", "permanent_resident"}


def policy_loan_type(product: dict[str, Any]) -> str | None:
    loan_type, category = product.get("loan_type"), product.get("category")
    if loan_type == "personal" and category == "vehicle":
        return "Car / Vehicle Loan"
    if loan_type == "personal":
        return "Secured Personal Loan" if product.get("secured") else "Unsecured Personal Loan"
    if loan_type == "home" and category == "investment":
        return "Investment Property Loan"
    if loan_type == "home" and category == "first_home":
        return "First Home Buyer Loan"
    if loan_type == "home":
        return "Owner-Occupied Home Loan"
    if loan_type == "business":
        return "Business Term Loan"
    return None


def _metric(metrics: dict[str, Any], name: str) -> Any:
    entry = metrics.get(name)
    if not entry or entry.get("state") != "computed":
        return None
    return entry.get("value")


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _money(value: float) -> str:
    return f"-${abs(value):,.0f}" if value < 0 else f"${value:,.0f}"


def _result(status: str, applicant_value: str | None, detail: str) -> dict[str, Any]:
    return {"status": status, "applicant_value": applicant_value, "detail": detail}


def _unparsed() -> dict[str, Any]:
    return _result("review", None, "This rule could not be checked automatically. Review it manually.")


def check_min_age(rule: str, filled: dict[str, Any], today: date) -> dict[str, Any]:
    match = re.search(r"(\d+)", rule)
    if not match:
        return _unparsed()
    minimum = int(match.group(1))
    try:
        dob = date.fromisoformat(str(filled.get("date_of_birth")))
    except ValueError:
        return _result("no_data", None, "Date of birth not provided.")
    age = int((today - dob).days // 365.25)
    if age >= minimum:
        return _result("pass", f"{age} years", f"Meets the minimum age of {minimum}.")
    return _result("exception", f"{age} years", f"Below the minimum age of {minimum}.")


def check_residency(filled: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    residency = filled.get("residency_status")
    if not residency:
        return _result("no_data", None, "Residency status not provided.")
    label = str(residency).replace("_", " ").capitalize()
    if residency in ACCEPTED_RESIDENCY:
        return _result("pass", label, "Accepted residency status.")
    if residency == "temporary_visa":
        shortfall = _number(_metric(metrics, "visa_shortfall_months"))
        if shortfall and shortfall > 0:
            return _result("exception", label, f"Visa ends {shortfall:.0f} months before the loan term.")
        return _result("review", label, "Temporary visa holder. Confirm the visa is acceptable.")
    return _result("review", label, "Residency status needs manual review.")


def check_loan_amount(rule: str, filled: dict[str, Any]) -> dict[str, Any]:
    match = re.search(r"\$([\d,]+)\s*-\s*\$([\d,]+)", rule)
    if not match:
        return _unparsed()
    low, high = (float(part.replace(",", "")) for part in match.groups())
    amount = _number(filled.get("loan_amount"))
    if amount is None:
        return _result("no_data", None, "Loan amount not provided.")
    if low <= amount <= high:
        return _result("pass", _money(amount), f"Within the {_money(low)} to {_money(high)} range.")
    side = "below the minimum" if amount < low else "above the maximum"
    limit = _money(low) if amount < low else _money(high)
    return _result("exception", _money(amount), f"Amount is {side} of {limit}.")


def check_max_term(rule: str, filled: dict[str, Any]) -> dict[str, Any]:
    match = re.search(r"(\d+)\s*years?", rule, re.IGNORECASE)
    if not match:
        return _unparsed()
    max_months = int(match.group(1)) * 12
    term = _number(filled.get("loan_term_months"))
    if term is None:
        return _result("no_data", None, "Loan term not provided.")
    if term <= max_months:
        return _result("pass", f"{term:.0f} months", f"Within the maximum of {max_months} months.")
    return _result("exception", f"{term:.0f} months", f"Longer than the maximum of {max_months} months.")


def check_deposit(rule: str, product: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    if "no deposit if unsecured" in rule.lower():
        if not product.get("secured"):
            return _result("not_applicable", None, "Unsecured product. No deposit is needed.")
        return _result("review", None, "Secured product. Confirm the security offered.")

    minimum = re.search(r"(\d+(?:\.\d+)?)%[^;]*minimum", rule, re.IGNORECASE)
    review_lvr = re.search(r">\s*(\d+(?:\.\d+)?)%\s*LVR", rule, re.IGNORECASE)
    if not minimum and not review_lvr:
        return _unparsed()

    contribution = _number(_metric(metrics, "contribution_pct"))
    if contribution is None:
        return _result("no_data", None, "Deposit or purchase price not provided.")
    lvr = 100 - contribution
    value = f"{contribution:.1f}% deposit · {lvr:.1f}% LVR"
    if minimum and contribution < float(minimum.group(1)):
        return _result("exception", value, f"Deposit is below the {minimum.group(1)}% minimum.")
    if review_lvr and lvr > float(review_lvr.group(1)):
        return _result("review", value, f"LVR is above {review_lvr.group(1)}%, so extra review is required.")
    return _result("pass", value, "Deposit and LVR are within policy.")


def check_income(filled: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    if filled.get("employment_status") == "unemployed":
        return _result("exception", "Unemployed", "No regular income declared.")
    income = _number(_metric(metrics, "gross_annual_income"))
    if income is None:
        return _result("no_data", None, "Income could not be assessed.")
    return _result("pass", f"{_money(income)} a year", "Regular income declared and assessed.")


def check_serviceability(metrics: dict[str, Any]) -> dict[str, Any]:
    surplus = _number(_metric(metrics, "monthly_surplus"))
    if surplus is None:
        return _result("no_data", None, "Serviceability could not be calculated.")
    value = f"{_money(surplus)} monthly surplus"
    if surplus < 0:
        return _result("exception", value, "Shortfall after the new repayment.")
    stressed = _number(_metric(metrics, "stressed_nsr"))
    if stressed is not None and stressed < 0:
        return _result("review", value, "Passes now but goes negative under an income shock.")
    return _result("pass", value, "Passes the serviceability assessment.")


def check_credit(metrics: dict[str, Any]) -> dict[str, Any]:
    adverse = []
    if (_number(_metric(metrics, "unpaid_defaults")) or 0) > 0:
        adverse.append("unpaid defaults")
    if (_number(_metric(metrics, "missed_payment_count_24mo")) or 0) > 0:
        adverse.append("missed payments")
    if (_number(_metric(metrics, "hardship_flags_12mo")) or 0) > 0:
        adverse.append("hardship flags")
    bankruptcy = _metric(metrics, "bankruptcy_judgment_status")
    if bankruptcy not in (None, "none"):
        adverse.append(str(bankruptcy).replace("_", " "))

    score = _metric(metrics, "credit_score")
    value = f"Score {score}" if score is not None else None
    if adverse:
        return _result("review", value, f"Adverse events found: {', '.join(adverse)}.")
    if score is None:
        return _result("no_data", None, "No credit report available.")
    return _result("pass", value, "No adverse events on the credit report.")


def evaluate_rule(
    category: str, rule: str, product: dict[str, Any], metrics: dict[str, Any], filled: dict[str, Any], today: date
) -> dict[str, Any]:
    if category == "Min Age":
        return check_min_age(rule, filled, today)
    if category == "Residency Policy":
        return check_residency(filled, metrics)
    if category == "Dummy Loan Amount":
        return check_loan_amount(rule, filled)
    if category == "Dummy Max Term":
        return check_max_term(rule, filled)
    if category == "Deposit / LVR Policy":
        return check_deposit(rule, product, metrics)
    if category == "Income / Cash Flow Policy":
        return check_income(filled, metrics)
    if category == "Serviceability Policy":
        return check_serviceability(metrics)
    if category == "Credit Policy":
        return check_credit(metrics)
    return _unparsed()


def _summary(checks: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"pass": 0, "exception": 0, "review": 0, "no_data": 0, "not_applicable": 0}
    for check in checks:
        counts[check["status"]] += 1
    return counts


def build_policy_check(
    rules: dict[str, str],
    bank: str,
    loan_type: str,
    product: dict[str, Any],
    metrics: dict[str, Any],
    filled: dict[str, Any],
    today: date | None = None,
) -> dict[str, Any]:
    today = today or date.today()
    checks = []
    for category, label in CATEGORY_ORDER:
        rule = rules.get(category)
        if not rule:
            continue
        checks.append({
            "category": category,
            "label": label,
            "policy_rule": rule,
            **evaluate_rule(category, rule, product, metrics, filled, today),
        })
    return {
        "status": "ok" if checks else "no_policy",
        "bank": bank,
        "loan_type": loan_type,
        "source": SOURCE,
        "data_status": DATA_STATUS,
        "checks": checks,
        "summary": _summary(checks),
    }


async def load_policy_rules(db: AsyncSession, bank: str, loan_type: str) -> dict[str, str]:
    result = await db.execute(
        select(PolicyChunk.category, PolicyChunk.content).where(
            func.lower(PolicyChunk.bank) == bank.lower(),
            func.lower(PolicyChunk.loan_type) == loan_type.lower(),
        )
    )
    rules = {}
    for category, content in result.all():
        rule = content.rsplit("Policy Rule:", 1)[-1].strip()
        rules[category] = rule
    return rules


async def run_policy_check(
    db: AsyncSession, product: dict[str, Any], metrics: dict[str, Any], filled: dict[str, Any]
) -> dict[str, Any]:
    bank = get_settings().policy_benchmark_bank
    loan_type = policy_loan_type(product)
    empty = {
        "bank": bank, "loan_type": loan_type, "source": SOURCE, "data_status": DATA_STATUS,
        "checks": [], "summary": _summary([]),
    }
    if loan_type is None:
        return {**empty, "status": "no_policy"}

    try:
        rules = await load_policy_rules(db, bank, loan_type)
    except SQLAlchemyError:
        await db.rollback()
        return {**empty, "status": "not_loaded"}

    if not rules:
        has_any = await db.scalar(select(func.count()).select_from(PolicyChunk))
        return {**empty, "status": "no_policy" if has_any else "not_loaded"}

    return build_policy_check(rules, bank, loan_type, product, metrics, filled)
