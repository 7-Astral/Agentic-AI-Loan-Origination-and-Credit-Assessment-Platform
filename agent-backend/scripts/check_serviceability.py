import sys
from decimal import Decimal

from app.agents.assessment.metric import Metric, MetricState
from app.agents.assessment.retail.approval_conditions import build_conditions
from app.agents.assessment.retail.metrics.capacity import FREQUENCY_PER_YEAR, assess_capacity
from app.agents.assessment.rules.engine import evaluate
from mock_core_banking.seed import POLICY_SETTINGS
from mock_core_banking.seed_rules import RULES

POLICIES = {p["key"]: p["document"] for p in POLICY_SETTINGS}
PRODUCT = {"product_code": "PL-STD-001", "loan_type": "personal", "category": "general", "secured": False,
           "interest_rate": 9.99, "rate_type": "fixed"}
RULE_IDS = {"nsr_minimum", "nsr_comfortable", "surplus_negative", "net_income_implausible"}
RULES_UNDER_TEST = [{"rule_id": r["rule_id"], "framework": r["framework"], **r["document"]} for r in RULES if r["rule_id"] in RULE_IDS]

BASE = {
    "employment_status": "full_time", "gross_annual_income": 95000, "net_income_amount": 2450,
    "net_income_frequency": "fortnightly", "dependants": 0, "marital_status": "single",
    "exp_food_groceries": 600, "exp_rent_board": 1400, "other_loan_repayments_monthly": 0,
    "credit_card_limit_total": 5000, "loan_amount": 20000, "loan_term_months": 60,
}

results: list[tuple[bool, str]] = []


def check(ok: bool, name: str, detail: str = "") -> None:
    results.append((ok, name))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'' if ok else '   -> ' + detail}")


def capacity(policies=None, **overrides) -> dict[str, Metric]:
    return assess_capacity({**BASE, **overrides}, PRODUCT, policies or POLICIES)


def fired(metrics: dict[str, Metric]) -> dict[str, str]:
    return {r["rule_id"]: r["status"] for r in evaluate(RULES_UNDER_TEST, metrics, "individual")}


def val(metrics, name):
    m = metrics[name]
    return m.value if m.usable else m.state.value


print("\nSurplus comes from take-home pay")
m = capacity()
net = Decimal(2450) * 26 / 12
check(val(m, "net_monthly_income") == net.quantize(Decimal("0.01")), "take-home per month is 2450 x 26 / 12", str(val(m, "net_monthly_income")))
check(val(m, "assessed_net_income") == val(m, "net_monthly_income"), "a full-time employee's take-home is not shaded")
expected = val(m, "assessed_net_income") - val(m, "assessed_living_expenses") - val(m, "existing_commitments") - val(m, "proposed_repayment")
check(val(m, "monthly_surplus") == expected.quantize(Decimal("0.01")), "surplus = take-home - expenses - commitments - repayment",
      f"{val(m, 'monthly_surplus')} vs {expected}")
gross_basis = Decimal(95000) / 12 - val(m, "assessed_living_expenses") - val(m, "existing_commitments") - val(m, "proposed_repayment")
check(val(m, "monthly_surplus") < gross_basis - 2000, "and it is well below what the gross-income method gave",
      f"{val(m, 'monthly_surplus')} vs gross basis {gross_basis:.2f}")
check(val(m, "nsr") == (val(m, "monthly_surplus") / val(m, "proposed_repayment")).quantize(Decimal("0.01")), "NSR is surplus over repayment")

print("\nShading applies to take-home")
m = capacity(employment_status="casual")
check(val(m, "assessed_net_income") == (val(m, "net_monthly_income") * Decimal("0.8")).quantize(Decimal("0.01")),
      "casual take-home is shaded to 80%", str(val(m, "assessed_net_income")))
m = capacity(employment_status="self_employed")
check(val(m, "assessed_net_income") == (val(m, "net_monthly_income") * Decimal("0.8")).quantize(Decimal("0.01")), "self-employed take-home is shaded to 80%")
legacy = {**POLICIES, "shading_rates": {"full_time_employed": 0.9}}
m = capacity(policies=legacy)
check(m["assessed_net_income"].inputs["shading_rate"] == 0.9, "an older policy keyed 'full_time_employed' still applies to 'full_time'")
current = {**POLICIES, "shading_rates": {"full_time": 0.85}}
m = capacity(policies=current)
check(m["assessed_net_income"].inputs["shading_rate"] == 0.85, "a policy keyed 'full_time' applies directly")
m = capacity(employment_status="retired")
check(m["assessed_net_income"].inputs["shading_rate"] == 1.0, "a status with no policy entry is not shaded")

print("\nMissing take-home is never replaced by gross")
m = capacity(net_income_amount=None)
check(val(m, "assessed_net_income") == "unavailable" and val(m, "monthly_surplus") == "unavailable" and val(m, "nsr") == "unavailable",
      "no take-home means no surplus and no NSR")
check(fired(m).get("nsr_minimum") == "provisional", "so the NSR rules wait on data")
m = capacity(net_income_frequency=None)
check(val(m, "monthly_surplus") == "unavailable", "no pay frequency means no surplus either")
check("annually" in FREQUENCY_PER_YEAR, "'annually' is a supported pay frequency")
m = capacity(net_income_amount=70000, net_income_frequency="annually")
check(val(m, "net_monthly_income") == Decimal("5833.33"), "70000 a year is 5833.33 a month", str(val(m, "net_monthly_income")))

print("\nDebt ratios stay on gross income")
m = capacity()
shaded = val(m, "shaded_income")
debt_service = (val(m, "existing_commitments") + val(m, "proposed_repayment")) * 12
check(val(m, "dti") == (debt_service / shaded).quantize(Decimal("0.001")), "DTI is annual debt service over gross income")
check(val(m, "dsr") == ((val(m, "existing_commitments") + val(m, "proposed_repayment")) / (shaded / 12)).quantize(Decimal("0.001")),
      "DSR is monthly debt service over gross monthly income")

print("\nAffordability rules")
m = capacity()
check(fired(m) == {}, "a comfortable applicant triggers nothing", str(fired(m)))
m = capacity(net_income_amount=1450, loan_amount=45000, loan_term_months=36, exp_food_groceries=900, exp_rent_board=1800)
check(fired(m).get("nsr_minimum") == "fail" and fired(m).get("surplus_negative") == "fail", "an overstretched borrower fails on take-home")

print("\nTake-home plausibility")
m = capacity()
check(Decimal("0.6") < val(m, "net_to_gross_ratio") < Decimal("0.8"), "a normal ratio is about 0.67", str(val(m, "net_to_gross_ratio")))
check("net_income_implausible" not in fired(m), "and is not flagged")
m = capacity(net_income_amount=3650)
check(val(m, "net_to_gross_ratio") > Decimal("0.95") and fired(m).get("net_income_implausible") == "flag",
      "take-home almost equal to gross is flagged", str(val(m, "net_to_gross_ratio")))
m = capacity(net_income_amount=1500)
check(val(m, "net_to_gross_ratio") < Decimal("0.5") and fired(m).get("net_income_implausible") == "flag", "take-home under half of gross is flagged",
      str(val(m, "net_to_gross_ratio")))
m = capacity(gross_annual_income=20000, net_income_amount=770)
check("net_income_implausible" not in fired(m), "a very low income is exempt, since little tax is paid")
m = capacity(gross_annual_income=None)
check(val(m, "net_to_gross_ratio") == "unavailable" and fired(m).get("net_income_implausible") == "provisional", "no gross income means the check waits")

print("\nCondition of approval")
m = capacity(net_income_amount=3650)
rules = [{"rule_id": rid, "status": st} for rid, st in fired(m).items()]
conditions = {c["id"]: c for c in build_conditions(BASE, PRODUCT, m, rules)}
check("net_income_evidence" in conditions and conditions["net_income_evidence"]["category"] == "capacity",
      "an implausible take-home asks for payslips and statements")

failed = [name for ok, name in results if not ok]
print(f"\n{len(results) - len(failed)} of {len(results)} checks passed")
if failed:
    print("FAILED:", *failed, sep="\n  ")
    sys.exit(1)
