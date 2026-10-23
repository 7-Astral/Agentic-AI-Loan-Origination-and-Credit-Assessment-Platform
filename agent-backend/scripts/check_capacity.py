import asyncio
from app.agents.assessment.retail.metrics.capacity import assess_capacity
from app.services.core_banking import core_banking

async def main():
    filled = {
        "gross_annual_income": 85000, "employment_status": "full_time_employed",
        "net_income_amount": 2200, "net_income_frequency": "fortnightly",
        "exp_food_groceries": 600, "exp_rent_board": 1400, "exp_insurance": 180,
        "dependants": 0, "marital_status": "single",
        "other_loan_repayments_monthly": 0, "credit_card_limit_total": 5000,
        "loan_amount": 35000, "loan_term_months": 60,
    }
    product = {"interest_rate": 6.89}
    policy = {
        "shading_rates": (await core_banking.get_policy("shading_rates"))["document"],
        "hem_benchmarks": (await core_banking.get_policy("hem_benchmarks"))["document"],
        "assessment_rate_buffer": (await core_banking.get_policy("assessment_rate_buffer"))["document"],
    }

    results = assess_capacity(filled, product, policy)
    for name, metric in results.items():
        print(f"{name:28} {metric.state.value:12} {metric.value}")

asyncio.run(main())