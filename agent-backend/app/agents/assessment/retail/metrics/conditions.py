from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.agents.assessment.metric import Channel, Metric, MetricState

CONDITIONS_METRIC_NAMES = [
    "loan_purpose",
    "purpose_eligibility",
    "loan_amount_and_term",
    "product_limit_breaches",
    "product_structure",
    "repayment_structure",
    "balloon_pct",
    "max_balloon_pct",
    "vehicle_age_assessed",
    "vehicle_age_limit",
    "age_at_maturity",
    "max_age_at_maturity",
    "visa_shortfall_months",
    "stressed_nsr",
    "employment_stability",
    "industry_sector_risk",
]

DEFAULT_CONDITIONS_POLICY: dict[str, Any] = {
    "excluded_purposes": {"personal": ["business_use"], "home": [], "business": []},
    "expected_purposes": {
        "vehicle": ["purchase_vehicle"],
        "owner_occupied": ["purchase_property", "home_improvement", "debt_consolidation"],
        "investment": ["purchase_property"],
    },
    "max_age_at_maturity": 70,
    "income_shock_pct": 10,
    "max_balloon_pct": 30,
    "vehicle_age_limits": {
        "VL-NEW-020": {"basis": "at_application", "max_years": 3},
        "VL-USED-021": {"basis": "at_end_of_term", "max_years": 12},
    },
    "min_tenure_months": {"full_time": 3, "part_time": 6, "casual": 12, "self_employed": 24},
    "ineligible_employment": ["unemployed", "student"],
    "review_employment": ["retired"],
    "industry_risk": {
        "construction": "high", "accommodation_food": "high", "arts_recreation": "high",
        "retail_trade": "medium", "agriculture_forestry_fishing": "medium", "mining": "medium",
        "transport_postal_warehousing": "medium", "administrative_support": "medium",
        "property_rental": "medium", "wholesale_trade": "medium", "manufacturing": "medium",
        "utilities": "low", "finance_insurance": "low", "information_media_telecom": "low",
        "professional_scientific_technical": "low", "public_administration_safety": "low",
        "education_training": "low", "health_care_social_assistance": "low", "other_services": "medium",
    },
}

WORKING_STATUSES = ("full_time", "part_time", "casual", "self_employed")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _computed(value, channel: Channel, **kwargs) -> Metric:
    return Metric(value=value, state=MetricState.COMPUTED, channel=channel, computed_at=_now(), **kwargs)


def _unavailable(channel: Channel, **kwargs) -> Metric:
    return Metric(value=None, state=MetricState.UNAVAILABLE, channel=channel, **kwargs)


def _not_applicable(channel: Channel) -> Metric:
    return Metric(value=None, state=MetricState.NOT_APPLICABLE, channel=channel)


def _to_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _months_between(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + end.month - start.month
    return months - 1 if end.day < start.day else months


def loan_purpose(filled: dict[str, Any]) -> Metric[str]:
    purpose = filled.get("loan_purpose")
    if purpose is None:
        return _unavailable(Channel.DECLARATION)
    return _computed(purpose, Channel.DECLARATION, inputs={"purpose_detail": filled.get("purpose_detail")})


def purpose_eligibility(filled: dict[str, Any], product: dict, policy: dict) -> Metric[str]:
    purpose = filled.get("loan_purpose")
    if purpose is None:
        return _unavailable(Channel.POLICY)

    category = product.get("category")
    if purpose in policy["excluded_purposes"].get(product.get("loan_type"), []):
        status = "excluded"
    elif purpose == "other":
        status = "needs_detail"
    else:
        expected = policy["expected_purposes"].get(category)
        status = "not_suited_to_product" if expected and purpose not in expected else "allowed"
    return _computed(status, Channel.POLICY, inputs={"purpose": purpose, "product_category": category})


def loan_amount_and_term(filled: dict[str, Any]) -> Metric[dict]:
    amount = filled.get("loan_amount")
    term = filled.get("loan_term_months")
    if amount is None or term is None:
        return _unavailable(Channel.DECLARATION)
    return _computed({"amount": amount, "term_months": term}, Channel.DECLARATION, unit="AUD / months")


def product_limit_breaches(filled: dict[str, Any], product: dict) -> Metric[int]:
    amount, term = filled.get("loan_amount"), filled.get("loan_term_months")
    if amount is None or term is None:
        return _unavailable(Channel.POLICY)

    limits = [
        ("amount", float(amount), product.get("min_amount"), product.get("max_amount"), "$"),
        ("term", float(term), product.get("min_term_months"), product.get("max_term_months"), ""),
    ]
    found = []
    for name, value, low, high, prefix in limits:
        suffix = " months" if name == "term" else ""
        if low is not None and value < low:
            found.append(f"{name} is below the {prefix}{low:,.0f}{suffix} minimum")
        if high is not None and value > high:
            found.append(f"{name} is above the {prefix}{high:,.0f}{suffix} maximum")
    return _computed(len(found), Channel.POLICY, unit="count", inputs={
        "breaches": "; ".join(found) or "none", "amount": float(amount), "term_months": float(term),
        "allowed_amount": f"{product.get('min_amount')} to {product.get('max_amount')}",
        "allowed_term_months": f"{product.get('min_term_months')} to {product.get('max_term_months')}",
    })


def product_structure(product: dict) -> Metric[dict]:
    rate_type = product.get("rate_type")
    secured = product.get("secured")
    if rate_type is None or secured is None:
        return _unavailable(Channel.DECLARATION)
    return _computed({"rate_type": rate_type, "secured": secured}, Channel.DECLARATION)


def repayment_structure(filled: dict[str, Any], product: dict) -> Metric[str]:
    if filled.get("repayment_type") == "interest_only":
        return _computed("interest_only", Channel.DECLARATION)
    if filled.get("wants_balloon") is True:
        return _computed("balloon", Channel.DECLARATION, inputs={"balloon_pct": filled.get("balloon_percentage")})
    if product.get("loan_type") == "home" and filled.get("repayment_type") is None:
        return _unavailable(Channel.DECLARATION)
    if product.get("category") == "vehicle" and filled.get("wants_balloon") is None:
        return _unavailable(Channel.DECLARATION)
    return _computed("principal_and_interest", Channel.DECLARATION)


def balloon(filled: dict[str, Any], product: dict, policy: dict) -> tuple[Metric, Metric]:
    if product.get("category") != "vehicle":
        return _not_applicable(Channel.DECLARATION), _not_applicable(Channel.POLICY)
    cap = policy.get("max_balloon_pct")
    cap_metric = _computed(cap, Channel.POLICY, unit="%") if cap is not None else _not_applicable(Channel.POLICY)

    wants = filled.get("wants_balloon")
    if wants is None:
        return _unavailable(Channel.DECLARATION), cap_metric
    if wants is False:
        return _computed(0, Channel.DECLARATION, unit="%"), cap_metric
    pct = filled.get("balloon_percentage")
    if pct is None:
        return _unavailable(Channel.DECLARATION), cap_metric
    return _computed(float(pct), Channel.DECLARATION, unit="%"), cap_metric


def vehicle_age(filled: dict[str, Any], product: dict, policy: dict, today: date) -> tuple[Metric, Metric]:
    limit = policy["vehicle_age_limits"].get(product.get("product_code"))
    if not limit:
        return _not_applicable(Channel.DECLARATION), _not_applicable(Channel.POLICY)

    limit_metric = _computed(limit["max_years"], Channel.POLICY, unit="years", inputs={"basis": limit["basis"]})
    year, term = filled.get("vehicle_year"), filled.get("loan_term_months")
    at_end = limit["basis"] == "at_end_of_term"
    if year is None or (at_end and term is None):
        return _unavailable(Channel.DECLARATION), limit_metric

    age = today.year - int(year) + (float(term) / 12 if at_end else 0)
    return _computed(round(age, 1), Channel.DERIVED, unit="years", inputs={
        "basis": limit["basis"], "vehicle_year": int(year),
    }), limit_metric


def age_at_maturity(filled: dict[str, Any], policy: dict, today: date) -> tuple[Metric, Metric]:
    cap = policy.get("max_age_at_maturity")
    cap_metric = _computed(cap, Channel.POLICY, unit="years") if cap is not None else _not_applicable(Channel.POLICY)

    dob, term = _to_date(filled.get("date_of_birth")), filled.get("loan_term_months")
    if dob is None or term is None:
        return _unavailable(Channel.DERIVED), cap_metric
    age_now = (today - dob).days / 365.25
    return _computed(round(age_now + float(term) / 12, 1), Channel.DERIVED, unit="years", inputs={
        "age_now": round(age_now, 1), "term_months": float(term),
    }), cap_metric


def visa_shortfall_months(filled: dict[str, Any], today: date) -> Metric[int]:
    residency = filled.get("residency_status")
    if residency is None:
        return _unavailable(Channel.DECLARATION)
    if residency != "temporary_visa":
        return _not_applicable(Channel.DECLARATION)

    expiry, term = _to_date(filled.get("visa_expiry_date")), filled.get("loan_term_months")
    if expiry is None or term is None:
        return _unavailable(Channel.DECLARATION)
    remaining = max(0, _months_between(today, expiry))
    return _computed(max(0, int(term) - remaining), Channel.DERIVED, unit="months", inputs={
        "visa_months_remaining": remaining, "loan_term_months": int(term),
    })


def stressed_nsr(capacity: dict[str, Metric] | None, policy: dict) -> Metric[Decimal]:
    needed = [(capacity or {}).get(name) for name in ("assessed_net_income", "monthly_surplus", "proposed_repayment")]
    if not all(m is not None and m.usable for m in needed) or needed[2].value == 0:
        return _unavailable(Channel.DERIVED)

    income, surplus, repayment = needed
    shock = Decimal(str(policy.get("income_shock_pct", 10))) / 100
    stressed_surplus = surplus.value - income.value * shock
    value = (stressed_surplus / repayment.value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.DERIVED, unit="ratio", inputs={
        "income_shock_pct": float(shock * 100), "stressed_surplus": float(stressed_surplus.quantize(Decimal("0.01"))),
        "repayment": float(repayment.value),
    })


def employment_stability(filled: dict[str, Any], policy: dict) -> Metric[str]:
    status = filled.get("employment_status")
    if status is None:
        return _unavailable(Channel.DECLARATION)
    if status in policy["ineligible_employment"]:
        return _computed("ineligible", Channel.POLICY, inputs={"employment_status": status})
    if status in policy["review_employment"]:
        return _computed("review", Channel.POLICY, inputs={"employment_status": status})

    minimum = policy["min_tenure_months"].get(status)
    if minimum is None:
        return _computed("stable", Channel.POLICY, inputs={"employment_status": status})

    years_trading = filled.get("abn_years_trading")
    if status == "self_employed" and years_trading is not None:
        months = float(years_trading) * 12
    else:
        months = filled.get("months_in_current_role")
    if months is None:
        return _unavailable(Channel.DECLARATION)

    on_probation = filled.get("on_probation") is True
    verdict = "stable" if months >= minimum and not on_probation else "review"
    return _computed(verdict, Channel.POLICY, inputs={
        "employment_status": status, "months_in_role": float(months), "minimum_months": minimum,
        "on_probation": on_probation,
    })


def industry_sector_risk(filled: dict[str, Any], policy: dict) -> Metric[str]:
    status = filled.get("employment_status")
    if status is None:
        return _unavailable(Channel.POLICY)
    if status not in WORKING_STATUSES:
        return _not_applicable(Channel.POLICY)

    industry = filled.get("employer_industry")
    if industry is None:
        return _unavailable(Channel.POLICY)
    return _computed(policy["industry_risk"].get(industry, "unclassified"), Channel.POLICY, inputs={"industry": industry})


def assess_conditions(
    filled: dict[str, Any],
    product: dict,
    policy: dict,
    capacity: dict[str, Metric] | None = None,
    today: date | None = None,
) -> dict[str, Metric]:
    today = today or date.today()
    rules = {**DEFAULT_CONDITIONS_POLICY, **(policy.get("conditions") or {})}

    balloon_pct, max_balloon_pct = balloon(filled, product, rules)
    vehicle_age_assessed, vehicle_age_limit = vehicle_age(filled, product, rules, today)
    maturity_age, max_maturity_age = age_at_maturity(filled, rules, today)

    return {
        "loan_purpose": loan_purpose(filled),
        "purpose_eligibility": purpose_eligibility(filled, product, rules),
        "loan_amount_and_term": loan_amount_and_term(filled),
        "product_limit_breaches": product_limit_breaches(filled, product),
        "product_structure": product_structure(product),
        "repayment_structure": repayment_structure(filled, product),
        "balloon_pct": balloon_pct,
        "max_balloon_pct": max_balloon_pct,
        "vehicle_age_assessed": vehicle_age_assessed,
        "vehicle_age_limit": vehicle_age_limit,
        "age_at_maturity": maturity_age,
        "max_age_at_maturity": max_maturity_age,
        "visa_shortfall_months": visa_shortfall_months(filled, today),
        "stressed_nsr": stressed_nsr(capacity, rules),
        "employment_stability": employment_stability(filled, rules),
        "industry_sector_risk": industry_sector_risk(filled, rules),
    }
