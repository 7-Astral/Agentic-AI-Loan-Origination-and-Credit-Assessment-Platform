from datetime import date

from app.agents.policy.check import build_policy_check, policy_loan_type

TODAY = date(2026, 10, 5)

HOME_RULES = {
    "Min Age": "18",
    "Residency Policy": "Accepted residency/legal status required",
    "Deposit / LVR Policy": "10% demo minimum; >80% LVR extra review",
    "Dummy Loan Amount": "$50,000-$2,000,000",
    "Dummy Max Term": "Up to 30 years",
    "Income / Cash Flow Policy": "Regular verifiable income required",
    "Serviceability Policy": "Must pass serviceability assessment",
    "Credit Policy": "Acceptable credit history; adverse events may require manual review",
}

HOME = {"loan_type": "home", "category": "owner_occupied", "secured": True}
PERSONAL = {"loan_type": "personal", "category": "general", "secured": False}


def computed(value):
    return {"state": "computed", "value": value}


def statuses(result):
    return {c["category"]: c["status"] for c in result["checks"]}


def test_maps_products_to_policy_loan_types():
    assert policy_loan_type(HOME) == "Owner-Occupied Home Loan"
    assert policy_loan_type(PERSONAL) == "Unsecured Personal Loan"
    assert policy_loan_type({"loan_type": "personal", "category": "vehicle"}) == "Car / Vehicle Loan"
    assert policy_loan_type({"loan_type": "business", "category": "term"}) == "Business Term Loan"
    assert policy_loan_type({"loan_type": "education"}) is None


def test_clean_home_application_passes_every_rule():
    metrics = {
        "contribution_pct": computed(25.0),
        "gross_annual_income": computed(120000),
        "monthly_surplus": computed(900),
        "stressed_nsr": computed(0.5),
        "credit_score": computed(780),
        "unpaid_defaults": computed(0),
        "missed_payment_count_24mo": computed(0),
        "bankruptcy_judgment_status": computed("none"),
    }
    filled = {
        "date_of_birth": "1990-05-01", "residency_status": "citizen",
        "loan_amount": 600000, "loan_term_months": 360, "employment_status": "full_time",
    }
    result = build_policy_check(HOME_RULES, "Bank", "Owner-Occupied Home Loan", HOME, metrics, filled, TODAY)

    assert result["status"] == "ok"
    assert set(statuses(result).values()) == {"pass"}
    assert result["summary"]["pass"] == 8


def test_breaches_are_exceptions_and_borderline_cases_need_review():
    metrics = {
        "contribution_pct": computed(15.0),
        "monthly_surplus": computed(-50),
        "credit_score": computed(700),
        "unpaid_defaults": computed(1),
    }
    filled = {
        "date_of_birth": "2010-01-01", "residency_status": "temporary_visa",
        "loan_amount": 3000000, "loan_term_months": 420,
    }
    result = build_policy_check(HOME_RULES, "Bank", "Owner-Occupied Home Loan", HOME, metrics, filled, TODAY)

    assert statuses(result) == {
        "Min Age": "exception",
        "Residency Policy": "review",
        "Dummy Loan Amount": "exception",
        "Dummy Max Term": "exception",
        "Deposit / LVR Policy": "review",
        "Income / Cash Flow Policy": "no_data",
        "Serviceability Policy": "exception",
        "Credit Policy": "review",
    }


def test_unsecured_loan_needs_no_deposit_and_missing_data_is_flagged():
    rules = {"Deposit / LVR Policy": "No deposit if unsecured; security if applicable", "Min Age": "18"}
    result = build_policy_check(rules, "Bank", "Unsecured Personal Loan", PERSONAL, {}, {}, TODAY)

    assert statuses(result) == {"Min Age": "no_data", "Deposit / LVR Policy": "not_applicable"}


def test_unreadable_rule_goes_to_manual_review():
    result = build_policy_check({"Dummy Max Term": "Depends on facility"}, "Bank", "X", HOME, {}, {}, TODAY)

    assert statuses(result) == {"Dummy Max Term": "review"}
