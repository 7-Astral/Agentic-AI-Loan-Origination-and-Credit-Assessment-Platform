import re
from datetime import date
from difflib import SequenceMatcher
from typing import Any
from app.core import observability

FUZZY_TEXT_THRESHOLD = 0.8
YEARS_TRADING_GRACE = 0.5
FINANCIALS_TOLERANCE_PCT = 5

RECONCILIATION_RULES: dict[str, list[dict]] = {
    "primary_photo_id": [
        {"extracted_field": "full_name", "slot_id": "full_name", "compare": "fuzzy_text"},
        {"extracted_field": "date_of_birth", "slot_id": "date_of_birth", "compare": "exact"},
    ],
    "proof_of_address": [
        {"extracted_field": "address", "slot_id": "current_address", "compare": "fuzzy_text"},
    ],
    "payslip_or_contract": [
        {"extracted_field": "employer_name", "slot_id": "employer_name", "compare": "fuzzy_text"},
    ],
    "payslip_or_tax_return": [
        {"extracted_field": "gross_annual_income", "slot_id": "gross_annual_income",
         "compare": "currency_tolerance", "tolerance_pct": 5},
    ],
    "bank_statements": [
        {"extracted_field": "account_holder_name", "slot_id": "full_name", "compare": "fuzzy_text"},
    ],
    "contract_of_sale": [
        {"extracted_field": "purchase_price", "slot_id": "vehicle_purchase_price",
         "compare": "currency_tolerance", "tolerance_pct": 2},
    ],
    "loan_statement": [
        {"extracted_field": "outstanding_balance", "slot_id": "mortgage_balance",
         "compare": "currency_tolerance", "tolerance_pct": 5},
    ],
}


def _financial(extracted_field: str, slot_id: str, optional: bool = False) -> dict:
    return {"extracted_field": extracted_field, "slot_id": slot_id, "compare": "currency_tolerance",
            "tolerance_pct": FINANCIALS_TOLERANCE_PCT, "optional": optional}


BUSINESS_RECONCILIATION_RULES: dict[str, list[dict]] = {
    "primary_photo_id": RECONCILIATION_RULES["primary_photo_id"],
    "business_registration": [
        {"extracted_field": "business_name", "slot_id": "business_name", "compare": "fuzzy_text"},
        {"extracted_field": "abn", "alt_extracted_fields": ["acn"], "slot_id": "abn_or_acn", "compare": "identifier"},
        {"extracted_field": "abn_active_from", "slot_id": "years_trading", "compare": "years_since"},
    ],
    "financial_statements": [
        {"extracted_field": "entity_name", "slot_id": "business_name", "compare": "fuzzy_text"},
        _financial("revenue", "annual_turnover"),
        _financial("net_profit_before_tax", "net_profit_before_tax"),
        _financial("interest_expense", "interest_expense_annual"),
        _financial("depreciation_amortisation", "depreciation_amortisation_annual"),
        _financial("current_assets", "current_assets"),
        _financial("current_liabilities", "current_liabilities"),
        _financial("total_liabilities", "total_business_liabilities"),
        _financial("total_equity", "total_business_equity"),
        _financial("prior_year_revenue", "prior_year_annual_turnover", optional=True),
        _financial("prior_year_net_profit_before_tax", "prior_year_net_profit_before_tax", optional=True),
        _financial("two_years_prior_revenue", "two_years_prior_annual_turnover", optional=True),
        _financial("two_years_prior_net_profit_before_tax", "two_years_prior_net_profit_before_tax", optional=True),
    ],
    "tax_return": [
        {"extracted_field": "taxpayer_name", "slot_id": "business_name", "alt_slot_ids": ["full_name"],
         "compare": "fuzzy_text"},
        {"extracted_field": "abn", "slot_id": "abn_or_acn", "compare": "identifier", "optional": True},
        {"extracted_field": "total_business_income", "slot_id": "annual_turnover",
         "compare": "currency_tolerance", "tolerance_pct": 10},
    ],
    "ato_position": [
        {"extracted_field": "abn", "slot_id": "abn_or_acn", "compare": "identifier", "optional": True},
        {"extracted_field": "overdue_amount", "alt_extracted_fields": ["outstanding_amount"],
         "slot_id": "ato_obligations_current", "compare": "no_debt"},
        {"extracted_field": "overdue_lodgments", "slot_id": "ato_obligations_current",
         "compare": "nothing_listed", "optional": True},
    ],
    "entity_documents": [
        {"extracted_field": "entity_name", "slot_id": "business_name", "compare": "fuzzy_text"},
    ],
    "bank_statements": [
        {"extracted_field": "account_holder_name", "slot_id": "business_name", "alt_slot_ids": ["full_name"],
         "compare": "fuzzy_text"},
        {"extracted_field": "annualised_sales_receipts", "slot_id": "annual_turnover",
         "compare": "currency_tolerance", "tolerance_pct": 30, "optional": True},
        {"extracted_field": "monthly_loan_repayments", "slot_id": "existing_business_debt_repayments",
         "compare": "currency_tolerance", "tolerance_pct": 20, "optional": True},
    ],
    "contract_of_sale": [
        {"extracted_field": "buyer_name", "slot_id": "business_name", "alt_slot_ids": ["full_name"],
         "compare": "fuzzy_text"},
        {"extracted_field": "purchase_price", "slot_id": "loan_amount", "compare": "not_less_than"},
    ],
}


def rules_for(verification_type: str, loan_type: str | None = None) -> list[dict] | None:
    if loan_type == "business":
        return BUSINESS_RECONCILIATION_RULES.get(verification_type)
    return RECONCILIATION_RULES.get(verification_type)


def _fuzzy_match(a: str, b: str) -> bool:
    a_norm = " ".join(str(a).strip().lower().split())
    b_norm = " ".join(str(b).strip().lower().split())
    return SequenceMatcher(None, a_norm, b_norm).ratio() >= FUZZY_TEXT_THRESHOLD


def _currency_match(declared: Any, extracted: Any, tolerance_pct: float) -> bool:
    try:
        d, e = float(declared), float(extracted)
    except (TypeError, ValueError):
        return False
    if d == 0:
        return e == 0
    return abs(d - e) / abs(d) <= (tolerance_pct / 100)


def _exact_match(declared: Any, extracted: Any) -> bool:
    return str(declared).strip() == str(extracted).strip()


def _identifier_match(declared: Any, extracted: Any) -> bool:
    d, e = re.sub(r"\D", "", str(declared)), re.sub(r"\D", "", str(extracted))
    return bool(d) and d == e


def _years_since_match(declared: Any, extracted: Any, today: date) -> bool:
    try:
        claimed = float(declared)
        since = date.fromisoformat(str(extracted)[:10])
    except (TypeError, ValueError):
        return False
    return claimed <= (today - since).days / 365.25 + YEARS_TRADING_GRACE


def _truthy(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("true", "yes", "1"):
        return True
    if text in ("false", "no", "0"):
        return False
    return None


def _no_debt_match(declared: Any, extracted: Any) -> bool:
    claimed_current = _truthy(declared)
    try:
        owing = float(extracted) > 0
    except (TypeError, ValueError):
        return False
    return claimed_current is not None and claimed_current == (not owing)


NOTHING_LISTED = {"none", "nil", "no", "0", "n/a", "na"}


def _nothing_listed_match(declared: Any, extracted: Any) -> bool:
    claimed_current = _truthy(declared)
    nothing = " ".join(str(extracted).strip().lower().split()) in NOTHING_LISTED
    return claimed_current is not None and claimed_current == nothing


def _not_less_than_match(declared: Any, extracted: Any) -> bool:
    try:
        return float(extracted) >= float(declared)
    except (TypeError, ValueError):
        return False


def _compare(rule: dict, declared: Any, extracted: Any, today: date) -> bool:
    compare = rule["compare"]
    if compare == "exact":
        return _exact_match(declared, extracted)
    if compare == "fuzzy_text":
        return _fuzzy_match(declared, extracted)
    if compare == "currency_tolerance":
        return _currency_match(declared, extracted, rule.get("tolerance_pct", 5))
    if compare == "identifier":
        return _identifier_match(declared, extracted)
    if compare == "years_since":
        return _years_since_match(declared, extracted, today)
    if compare == "no_debt":
        return _no_debt_match(declared, extracted)
    if compare == "nothing_listed":
        return _nothing_listed_match(declared, extracted)
    if compare == "not_less_than":
        return _not_less_than_match(declared, extracted)
    return False


def _present(source: dict[str, Any], keys: list[str]) -> list[Any]:
    return [source[k] for k in keys if source.get(k) not in (None, "")]


@observability.traced("document.reconcile")
def reconcile(
    verification_type: str, extracted_fields: dict[str, Any], filled: dict[str, Any],
    loan_type: str | None = None, today: date | None = None,
) -> list[dict]:
    rules = rules_for(verification_type, loan_type)
    today = today or date.today()

    if not rules:
        return [{
            "slot_id": "", "declared_value": "",
            "extracted_value": str(extracted_fields), "status": "on_file",
        }]

    results = []
    for rule in rules:
        slot_id = rule["slot_id"]
        extracted = _present(extracted_fields, [rule["extracted_field"], *rule.get("alt_extracted_fields", [])])
        declared = _present(filled, [slot_id, *rule.get("alt_slot_ids", [])])

        if not declared or not extracted:
            if rule.get("optional") and not extracted:
                continue
            results.append({
                "slot_id": slot_id,
                "declared_value": str(declared[0]) if declared else "",
                "extracted_value": str(extracted[0]) if extracted else "",
                "status": "missing",
            })
            continue

        pairs = [(d, e) for d in declared for e in extracted]
        matched = next(((d, e) for d, e in pairs if _compare(rule, d, e, today)), None)
        shown_declared, shown_extracted = matched or pairs[0]

        results.append({
            "slot_id": slot_id,
            "declared_value": str(shown_declared),
            "extracted_value": str(shown_extracted),
            "status": "match" if matched else "mismatch",
        })

    return results
