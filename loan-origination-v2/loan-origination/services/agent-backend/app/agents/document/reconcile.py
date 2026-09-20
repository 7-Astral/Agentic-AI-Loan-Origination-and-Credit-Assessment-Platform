from difflib import SequenceMatcher
from typing import Any

FUZZY_TEXT_THRESHOLD = 0.8

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


def reconcile(verification_type: str, extracted_fields: dict[str, Any], filled: dict[str, Any]) -> list[dict]:
    """Returns [{slot_id, declared_value, extracted_value, status}], status
    one of: match, mismatch, on_file, missing."""
    rules = RECONCILIATION_RULES.get(verification_type)

    if not rules:
        return [{
            "slot_id": "", "declared_value": "",
            "extracted_value": str(extracted_fields), "status": "on_file",
        }]

    results = []
    for rule in rules:
        slot_id = rule["slot_id"]
        extracted_value = extracted_fields.get(rule["extracted_field"])
        declared_value = filled.get(slot_id)

        if declared_value is None or extracted_value is None:
            results.append({
                "slot_id": slot_id,
                "declared_value": str(declared_value) if declared_value is not None else "",
                "extracted_value": str(extracted_value) if extracted_value is not None else "",
                "status": "missing",
            })
            continue

        compare = rule["compare"]
        if compare == "exact":
            is_match = _exact_match(declared_value, extracted_value)
        elif compare == "fuzzy_text":
            is_match = _fuzzy_match(declared_value, extracted_value)
        elif compare == "currency_tolerance":
            is_match = _currency_match(declared_value, extracted_value, rule.get("tolerance_pct", 5))
        else:
            is_match = False

        results.append({
            "slot_id": slot_id,
            "declared_value": str(declared_value),
            "extracted_value": str(extracted_value),
            "status": "match" if is_match else "mismatch",
        })

    return results