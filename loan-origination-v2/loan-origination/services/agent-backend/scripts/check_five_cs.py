import asyncio

from app.agents.assessment.retail.metrics.capacity import assess_capacity
from app.agents.assessment.retail.metrics.conditions import assess_conditions
from app.agents.assessment.retail.metrics.character import assess_character
from app.agents.assessment.retail.metrics.capital import assess_capital
from app.agents.assessment.retail.metrics.collateral import assess_collateral
from app.agents.assessment.rules.engine import evaluate
from app.services.core_banking import core_banking


async def main():
    filled = {
        "gross_annual_income": 85000, "employment_status": "full_time_employed",
        "net_income_amount": 2200, "net_income_frequency": "fortnightly",
        "exp_food_groceries": 600, "exp_rent_board": 1400, "exp_insurance": 180,
        "dependants": 0, "marital_status": "single",
        "other_loan_repayments_monthly": 0, "credit_card_limit_total": 5000,
        "loan_amount": 35000, "loan_term_months": 60,
        "loan_purpose": "purchase_vehicle", "employer_name": "Bunnings Warehouse",
    }
    product = {"interest_rate": 6.89, "rate_type": "fixed", "secured": True}
    policy = {
        "shading_rates": (await core_banking.get_policy("shading_rates"))["document"],
        "hem_benchmarks": (await core_banking.get_policy("hem_benchmarks"))["document"],
        "assessment_rate_buffer": (await core_banking.get_policy("assessment_rate_buffer"))["document"],
        "industry_risk": {},
    }

    metrics = {}
    metrics.update(assess_capacity(filled, product, policy))
    metrics.update(assess_conditions(filled, product, policy))
    metrics.update(assess_character(filled))
    metrics.update(assess_capital(filled))
    metrics.update(assess_collateral(filled))

    for name, metric in metrics.items():
        print(f"{name:30} {metric.state.value:15} {metric.value}")

    computed = sum(1 for m in metrics.values() if m.usable)
    print(f"\n{computed}/{len(metrics)} metrics computed, {len(metrics) - computed} unavailable")

    rules = await core_banking.get_rules("individual")
    results = evaluate(rules, metrics, "individual")

    print("\n--- Rule results ---")
    for r in results:
        label = r.get("message") or r.get("missing") or ""
        print(f"{r['rule_id']:20} {r['status']:12} {label}")


asyncio.run(main())
