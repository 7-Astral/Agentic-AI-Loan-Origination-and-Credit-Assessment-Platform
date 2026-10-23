import sys
from datetime import date
from decimal import Decimal

from app.agents.assessment.metric import Channel, Metric, MetricState
from app.agents.assessment.retail.approval_conditions import build_conditions
from app.agents.assessment.retail.metrics.capacity import assess_capacity
from app.agents.assessment.retail.metrics.conditions import (
    CONDITIONS_METRIC_NAMES,
    DEFAULT_CONDITIONS_POLICY,
    assess_conditions,
)
from app.agents.assessment.rules.engine import evaluate
from mock_core_banking.seed import CONDITIONS_POLICY, POLICY_SETTINGS
from mock_core_banking.seed_rules import RULES

TODAY = date(2026, 9, 21)
POLICIES = {p["key"]: p["document"] for p in POLICY_SETTINGS}
CONDITION_RULES = [
    {"rule_id": r["rule_id"], "framework": r["framework"], **r["document"]}
    for r in RULES
    if r["rule_id"] in {
        "purpose_excluded", "purpose_not_suited", "purpose_needs_detail", "product_limits_breached",
        "visa_expires_before_term_end", "age_at_maturity_high", "vehicle_too_old", "balloon_above_limit",
        "non_standard_repayment", "stressed_nsr_low", "employment_ineligible", "employment_review", "industry_high_risk",
    }
]

PRODUCTS = {
    "PL": {"product_code": "PL-STD-001", "loan_type": "personal", "category": "general", "secured": False,
           "interest_rate": 9.99, "rate_type": "fixed", "min_amount": 5000, "max_amount": 50000,
           "min_term_months": 12, "max_term_months": 84, "max_lvr": None},
    "VN": {"product_code": "VL-NEW-020", "loan_type": "personal", "category": "vehicle", "secured": True,
           "interest_rate": 6.89, "rate_type": "fixed", "min_amount": 10000, "max_amount": 150000,
           "min_term_months": 12, "max_term_months": 84, "max_lvr": None},
    "VU": {"product_code": "VL-USED-021", "loan_type": "personal", "category": "vehicle", "secured": True,
           "interest_rate": 8.49, "rate_type": "fixed", "min_amount": 8000, "max_amount": 100000,
           "min_term_months": 12, "max_term_months": 72, "max_lvr": None},
    "HL": {"product_code": "HL-VAR-010", "loan_type": "home", "category": "owner_occupied", "secured": True,
           "interest_rate": 5.94, "rate_type": "variable", "min_amount": 100000, "max_amount": 2000000,
           "min_term_months": 60, "max_term_months": 360, "max_lvr": 95},
}

BASE = {
    "full_name": "Jane Citizen", "date_of_birth": "1990-05-14", "residency_status": "citizen",
    "employment_status": "full_time", "months_in_current_role": 36, "employer_industry": "professional_scientific_technical",
    "gross_annual_income": 95000, "net_income_amount": 2450, "net_income_frequency": "fortnightly",
    "dependants": 0, "marital_status": "single", "exp_food_groceries": 600, "exp_rent_board": 1400,
    "other_loan_repayments_monthly": 0, "credit_card_limit_total": 5000,
    "loan_amount": 20000, "loan_term_months": 60, "loan_purpose": "debt_consolidation",
}

results: list[tuple[bool, str]] = []


def check(ok: bool, name: str, detail: str = "") -> None:
    results.append((ok, name))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'' if ok else '   -> ' + detail}")


def run(product: str, **overrides) -> tuple[dict[str, Metric], dict[str, str]]:
    """Conditions metrics and {rule_id: status} for the rules that fired or are waiting on data."""
    filled = {**BASE, **overrides}
    prod = PRODUCTS[product]
    policy = {**POLICIES}
    capacity = assess_capacity(filled, prod, policy)
    metrics = assess_conditions(filled, prod, policy, capacity, today=TODAY)
    fired = {r["rule_id"]: r["status"] for r in evaluate(CONDITION_RULES, metrics, "individual")}
    return metrics, fired


def value(metrics, name):
    m = metrics[name]
    return m.value if m.usable else m.state.value


def section(title: str) -> None:
    print(f"\n{title}")


section("Setup")
check(set(CONDITIONS_METRIC_NAMES) == set(assess_conditions(BASE, PRODUCTS["PL"], POLICIES, {}, TODAY)),
      "every listed metric is produced")
check(CONDITIONS_POLICY == DEFAULT_CONDITIONS_POLICY, "code default policy matches the seeded policy")

section("Baseline: a clean personal loan")
m, fired = run("PL")
check(fired == {}, "no conditions rule fires", str(fired))
check(value(m, "purpose_eligibility") == "allowed", "purpose allowed")
check(value(m, "product_limit_breaches") == 0, "within product limits")
check(value(m, "visa_shortfall_months") == "not_applicable", "visa not applicable to a citizen")
check(value(m, "vehicle_age_assessed") == "not_applicable", "vehicle age not applicable")
check(value(m, "balloon_pct") == "not_applicable", "balloon not applicable")
check(value(m, "repayment_structure") == "principal_and_interest", "standard repayments")
check(value(m, "employment_stability") == "stable", "employment stable")
check(value(m, "industry_sector_risk") == "low", "industry low risk")
check(41.0 < value(m, "age_at_maturity") < 42.0, "age at maturity about 41", str(value(m, "age_at_maturity")))
check(value(m, "stressed_nsr") > 1, "stressed NSR above 1", str(value(m, "stressed_nsr")))

section("Purpose")
_, fired = run("PL", loan_purpose="business_use")
check(fired.get("purpose_excluded") == "fail", "business use on a personal loan is excluded")
_, fired = run("PL", loan_purpose="other")
check(fired.get("purpose_needs_detail") == "flag", "'other' needs detail")
_, fired = run("VN", loan_purpose="travel", loan_amount=30000)
check(fired.get("purpose_not_suited") == "flag", "travel is not suited to a vehicle loan")
_, fired = run("HL", loan_purpose="purchase_property", loan_amount=450000, loan_term_months=300, repayment_type="principal_and_interest")
check("purpose_not_suited" not in fired and "purpose_excluded" not in fired, "property purchase suits a home loan", str(fired))
m, fired = run("PL", loan_purpose=None)
check(value(m, "purpose_eligibility") == "unavailable" and fired.get("purpose_excluded") == "provisional",
      "missing purpose makes the purpose rules wait")

section("Product limits")
m, fired = run("PL", loan_amount=60000)
check(fired.get("product_limits_breached") == "fail", "amount above the maximum fails")
check("above the $50,000 maximum" in m["product_limit_breaches"].inputs["breaches"], "the breach is described",
      str(m["product_limit_breaches"].inputs))
m, fired = run("PL", loan_amount=1000, loan_term_months=6)
check(value(m, "product_limit_breaches") == 2, "amount and term both below minimum count as two breaches")
_, fired = run("PL", loan_amount=5000, loan_term_months=84)
check("product_limits_breached" not in fired, "exactly on the limits is allowed")

section("Residency and visa")
_, fired = run("PL", residency_status="temporary_visa", visa_expiry_date="2028-03-21")
check(fired.get("visa_expires_before_term_end") == "flag", "visa ending in 18 months against a 60 month term is flagged")
m, fired = run("PL", residency_status="temporary_visa", visa_expiry_date="2031-09-21")
check(value(m, "visa_shortfall_months") == 0 and "visa_expires_before_term_end" not in fired, "visa covering the term is fine")
m, fired = run("PL", residency_status="temporary_visa")
check(fired.get("visa_expires_before_term_end") == "provisional", "temporary visa without an expiry date waits on data")
m, fired = run("PL", residency_status="permanent_resident")
check(value(m, "visa_shortfall_months") == "not_applicable" and "visa_expires_before_term_end" not in fired,
      "permanent resident skips the visa rule")

section("Age at maturity")
m, fired = run("HL", loan_purpose="purchase_property", loan_amount=300000, loan_term_months=300,
               repayment_type="principal_and_interest", date_of_birth="1958-01-01")
check(fired.get("age_at_maturity_high") == "flag", "a 68 year old on a 25 year term is flagged", str(value(m, "age_at_maturity")))
_, fired = run("HL", loan_purpose="purchase_property", loan_amount=300000, loan_term_months=300, repayment_type="principal_and_interest")
check("age_at_maturity_high" not in fired, "a 36 year old is not flagged")

section("Vehicle age")
m, fired = run("VU", loan_purpose="purchase_vehicle", vehicle_year=2010, loan_amount=15000, wants_balloon=False)
check(fired.get("vehicle_too_old") == "fail", "2010 vehicle over a 5 year term is too old at the end", str(value(m, "vehicle_age_assessed")))
_, fired = run("VU", loan_purpose="purchase_vehicle", vehicle_year=2022, loan_amount=15000, wants_balloon=False)
check("vehicle_too_old" not in fired, "a 2022 used vehicle is fine")
m, fired = run("VN", loan_purpose="purchase_vehicle", vehicle_year=2020, loan_amount=30000, wants_balloon=False)
check(fired.get("vehicle_too_old") == "fail" and m["vehicle_age_assessed"].inputs["basis"] == "at_application",
      "a new-vehicle product judges age at application")
_, fired = run("VN", loan_purpose="purchase_vehicle", vehicle_year=2025, loan_amount=30000, wants_balloon=False)
check("vehicle_too_old" not in fired, "a 2025 vehicle suits the new-vehicle product")
m, _ = run("VU", loan_purpose="purchase_vehicle", loan_amount=15000, wants_balloon=False)
check(value(m, "vehicle_age_assessed") == "unavailable", "no vehicle year means the age waits on data")

section("Repayment structure and balloon")
m, fired = run("VN", loan_purpose="purchase_vehicle", vehicle_year=2025, loan_amount=30000, wants_balloon=True, balloon_percentage=40)
check(fired.get("balloon_above_limit") == "flag" and fired.get("non_standard_repayment") == "flag", "a 40% balloon breaks the cap")
_, fired = run("VN", loan_purpose="purchase_vehicle", vehicle_year=2025, loan_amount=30000, wants_balloon=True, balloon_percentage=20)
check(fired.get("non_standard_repayment") == "flag" and "balloon_above_limit" not in fired, "a 20% balloon is non-standard but within the cap")
m, fired = run("VN", loan_purpose="purchase_vehicle", vehicle_year=2025, loan_amount=30000, wants_balloon=False)
check(value(m, "balloon_pct") == 0 and fired == {}, "no balloon means nothing to flag", str(fired))
_, fired = run("HL", loan_purpose="purchase_property", loan_amount=450000, loan_term_months=300, repayment_type="interest_only")
check(fired.get("non_standard_repayment") == "flag", "interest-only is flagged")
m, fired = run("HL", loan_purpose="purchase_property", loan_amount=450000, loan_term_months=300)
check(value(m, "repayment_structure") == "unavailable", "a home loan without a repayment type waits on data")

section("Stressed NSR (income falls by the policy shock)")
def capacity_with(income, surplus, repayment):
    def usable(v):
        return Metric(value=Decimal(v), state=MetricState.COMPUTED, channel=Channel.DERIVED)
    return {"assessed_net_income": usable(income), "monthly_surplus": usable(surplus), "proposed_repayment": usable(repayment)}

tight = assess_conditions(BASE, PRODUCTS["PL"], POLICIES, capacity_with(5000, 600, 550), TODAY)
check(tight["stressed_nsr"].value == Decimal("0.18"), "600 surplus less 10% of 5000 monthly take-home over a 550 repayment", str(tight["stressed_nsr"].value))
check(evaluate(CONDITION_RULES, tight, "individual")[0]["rule_id"] == "stressed_nsr_low", "and the rule flags it")
roomy = assess_conditions(BASE, PRODUCTS["PL"], POLICIES, capacity_with(5000, 3000, 550), TODAY)
check(roomy["stressed_nsr"].value == Decimal("4.55"), "a comfortable surplus survives the shock", str(roomy["stressed_nsr"].value))
check(assess_conditions(BASE, PRODUCTS["PL"], POLICIES, None, TODAY)["stressed_nsr"].state == MetricState.UNAVAILABLE,
      "without capacity figures the stress test waits")

section("Employment stability")
def stability(**kw):
    m, fired = run("PL", **kw)
    return value(m, "employment_stability"), fired
verdict, fired = stability(employment_status="unemployed")
check(verdict == "ineligible" and fired.get("employment_ineligible") == "fail", "unemployed is ineligible")
verdict, _ = stability(employment_status="student")
check(verdict == "ineligible", "student is ineligible")
verdict, fired = stability(employment_status="casual", months_in_current_role=4)
check(verdict == "review" and fired.get("employment_review") == "flag", "casual for 4 months (minimum 12) needs review")
verdict, _ = stability(employment_status="casual", months_in_current_role=14)
check(verdict == "stable", "casual for 14 months is stable")
verdict, _ = stability(months_in_current_role=36, on_probation=True)
check(verdict == "review", "on probation needs review")
verdict, _ = stability(employment_status="retired")
check(verdict == "review", "retired needs review")
verdict, _ = stability(employment_status="self_employed", abn_years_trading=1)
check(verdict == "review", "self-employed for 1 year (minimum 2) needs review")
verdict, _ = stability(employment_status="self_employed", abn_years_trading=3)
check(verdict == "stable", "self-employed for 3 years is stable")
verdict, fired = stability(employment_status="casual", months_in_current_role=None)
check(verdict == "unavailable" and fired.get("employment_review") == "provisional", "unknown tenure waits on data")

section("Industry")
m, fired = run("PL", employer_industry="construction")
check(value(m, "industry_sector_risk") == "high" and fired.get("industry_high_risk") == "flag", "construction is high risk")
m, _ = run("PL", employer_industry="something_new")
check(value(m, "industry_sector_risk") == "unclassified", "an industry not in the table is unclassified")
m, fired = run("PL", employer_industry=None)
check(fired.get("industry_high_risk") == "provisional", "missing industry waits on data")
m, fired = run("PL", employment_status="retired", employer_industry=None)
check(value(m, "industry_sector_risk") == "not_applicable" and "industry_high_risk" not in fired, "retired has no industry to assess")

section("Policy drives the result")
filled = {**BASE, "loan_purpose": "business_use"}
relaxed = assess_conditions(filled, PRODUCTS["PL"], {**POLICIES, "conditions": {**CONDITIONS_POLICY, "excluded_purposes": {"personal": []}}},
                            assess_capacity(filled, PRODUCTS["PL"], POLICIES), TODAY)
check(relaxed["purpose_eligibility"].value == "allowed", "removing the exclusion from policy allows the purpose")
strict = assess_conditions(BASE, PRODUCTS["PL"], {**POLICIES, "conditions": {**CONDITIONS_POLICY, "max_age_at_maturity": 30}}, None, TODAY)
check(strict["max_age_at_maturity"].value == 30, "the age cap comes from policy")
without = {k: v for k, v in POLICIES.items() if k != "conditions"}
fallback = assess_conditions(filled, PRODUCTS["PL"], without, None, TODAY)
check(fallback["purpose_eligibility"].value == "excluded", "a bank with no conditions policy gets the defaults")

section("Conditions of approval")
def approvals(product, rule_status=None, filled_extra=None, metrics_extra=None):
    filled = {**BASE, **(filled_extra or {})}
    metrics = {**assess_conditions(filled, PRODUCTS[product], POLICIES, assess_capacity(filled, PRODUCTS[product], POLICIES), TODAY),
               **(metrics_extra or {})}
    rules = [{"rule_id": rid, "status": st} for rid, st in (rule_status or {}).items()]
    return {c["id"]: c for c in build_conditions(filled, PRODUCTS[product], metrics, rules)}

got = approvals("PL")
check(set(got) == {"credit_report", "debt_payout"}, "unsecured debt consolidation: credit report and payout of debts", str(set(got)))
check(got["credit_report"]["category"] == "character" and got["debt_payout"]["category"] == "conditions", "each is filed under its C")
got = approvals("VN", filled_extra={"loan_purpose": "purchase_vehicle", "credit_check_consent": True},
                metrics_extra={"credit_score": Metric(value=800, state=MetricState.COMPUTED, channel=Channel.BUREAU)})
check(set(got) == {"valuation", "contract_of_sale", "vehicle_insurance"}, "vehicle loan: valuation, contract, insurance", str(set(got)))
got = approvals("HL", {"contribution_lmi_likely": "flag", "age_at_maturity_high": "flag", "employment_review": "flag",
                       "non_standard_repayment": "flag", "stressed_nsr_low": "flag", "industry_high_risk": "flag"},
                {"loan_purpose": "purchase_property", "deposit_amount": 80000, "deposit_source": "gift", "has_guarantor": True,
                 "residency_status": "temporary_visa"})
expected = {"credit_report", "income_buffer", "lmi", "deposit_evidence", "valuation", "building_insurance", "contract_of_sale",
            "guarantor", "exit_strategy", "visa_evidence", "employment_confirmation", "structure_suitability", "industry_confirmation"}
check(set(got) == expected, "a complicated home loan gets every relevant condition", str(set(got) ^ expected))
check("gift letter" in got["deposit_evidence"]["text"], "a gifted deposit asks for a gift letter")
check(got["income_buffer"]["blocking"] is False and got["industry_confirmation"]["blocking"] is False and got["lmi"]["blocking"] is True,
      "advisory conditions are marked as not blocking")
order = [c["category"] for c in build_conditions({**BASE, "has_guarantor": True}, PRODUCTS["HL"], {}, [])]
check(order == sorted(order, key=["capacity", "capital", "character", "collateral", "conditions"].index), "listed in five Cs order")

failed = [name for ok, name in results if not ok]
print(f"\n{len(results) - len(failed)} of {len(results)} checks passed")
if failed:
    print("FAILED:", *failed, sep="\n  ")
    sys.exit(1)
