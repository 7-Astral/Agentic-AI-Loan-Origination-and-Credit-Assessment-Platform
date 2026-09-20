import asyncio

from sqlalchemy import select

from mock_core_banking.db import engine, async_session
from mock_core_banking.models import Base, Rule
from mock_core_banking.seed import DEFAULT_BANK_ID

RULES = [
    {
        "rule_id": "nsr_minimum", "framework": "individual",
        "document": {
            "requires": ["nsr"], "when": "nsr < 1.0", "status": "fail",
            "message": "Surplus doesn't cover the proposed repayment",
        },
    },
    {
        "rule_id": "nsr_comfortable", "framework": "individual",
        "document": {
            "requires": ["nsr"], "when": "nsr >= 1.0 and nsr < 1.2", "status": "flag",
            "message": "Surplus covers repayment but with limited buffer",
        },
    },
    {
        "rule_id": "dti_high", "framework": "individual",
        "document": {
            "requires": ["dti"], "when": "dti > 0.45", "status": "flag",
            "message": "Overall debt-to-income ratio is elevated",
        },
    },
    {
        "rule_id": "surplus_negative", "framework": "individual",
        "document": {
            "requires": ["monthly_surplus"], "when": "monthly_surplus < 0", "status": "fail",
            "message": "Negative monthly surplus after all commitments",
        },
    },
    {
        "rule_id": "character_required", "framework": "individual",
        "document": {
            "requires": ["credit_score"], "when": "credit_score < 0", "status": "flag",
            "message": "Credit character checks not yet available",
        },
    },
    {
        "rule_id": "contribution_below_minimum", "framework": "individual",
        "document": {
            "requires": ["contribution_pct", "required_contribution_pct"],
            "when": "contribution_pct < required_contribution_pct", "status": "fail",
            "message": "Deposit is below the minimum contribution for this product",
        },
    },
    {
        "rule_id": "contribution_lmi_likely", "framework": "individual",
        "document": {
            "requires": ["contribution_pct", "required_contribution_pct"],
            "when": "contribution_pct >= required_contribution_pct and contribution_pct < 20",
            "status": "flag",
            "message": "Deposit is under 20% of the purchase price; lenders mortgage insurance is likely to apply",
        },
    },
    {
        "rule_id": "net_assets_negative", "framework": "individual",
        "document": {
            "requires": ["net_asset_position"], "when": "net_asset_position < 0", "status": "flag",
            "message": "Declared liabilities exceed declared assets",
        },
    },
    {
        "rule_id": "credit_score_very_low", "framework": "individual",
        "document": {
            "requires": ["credit_score"], "when": "credit_score < 400", "status": "fail",
            "message": "Credit score is in the lowest range",
        },
    },
    {
        "rule_id": "credit_score_low", "framework": "individual",
        "document": {
            "requires": ["credit_score"], "when": "credit_score >= 400 and credit_score < 622",
            "status": "flag", "message": "Credit score is below the 'good' band",
        },
    },
    {
        "rule_id": "unpaid_default_present", "framework": "individual",
        "document": {
            "requires": ["unpaid_defaults"], "when": "unpaid_defaults > 0", "status": "fail",
            "message": "Unpaid default listed on the credit file",
        },
    },
    {
        "rule_id": "paid_default_present", "framework": "individual",
        "document": {
            "requires": ["paid_defaults"], "when": "paid_defaults > 0", "status": "flag",
            "message": "Previous default (since paid) on the credit file",
        },
    },
    {
        "rule_id": "bankruptcy_or_judgment", "framework": "individual",
        "document": {
            "requires": ["bankruptcy_judgment_status"], "when": "bankruptcy_judgment_status != 'none'",
            "status": "fail", "message": "Bankruptcy, debt agreement or unsatisfied court judgment on file",
        },
    },
    {
        "rule_id": "severe_arrears_24mo", "framework": "individual",
        "document": {
            "requires": ["worst_rhi_24mo"], "when": "worst_rhi_24mo >= 3", "status": "fail",
            "message": "Account 90 or more days overdue in the last 24 months",
        },
    },
    {
        "rule_id": "recent_arrears_6mo", "framework": "individual",
        "document": {
            "requires": ["worst_rhi_6mo"], "when": "worst_rhi_6mo >= 1", "status": "flag",
            "message": "Late payment in the last 6 months",
        },
    },
    {
        "rule_id": "repeated_missed_payments", "framework": "individual",
        "document": {
            "requires": ["missed_payment_count_24mo"], "when": "missed_payment_count_24mo >= 3",
            "status": "flag", "message": "Three or more late payments in the last 24 months",
        },
    },
    {
        "rule_id": "enquiry_velocity_high", "framework": "individual",
        "document": {
            "requires": ["enquiry_velocity_6mo"], "when": "enquiry_velocity_6mo >= 5", "status": "flag",
            "message": "Five or more credit enquiries in the last 6 months",
        },
    },
    {
        "rule_id": "hardship_recent", "framework": "individual",
        "document": {
            "requires": ["hardship_flags_12mo"], "when": "hardship_flags_12mo > 0", "status": "flag",
            "message": "Financial hardship arrangement in the last 12 months",
        },
    },
    {
        "rule_id": "undisclosed_liabilities_material", "framework": "individual",
        "document": {
            "requires": ["undisclosed_liabilities"], "when": "undisclosed_liabilities > 100",
            "status": "flag",
            "message": "Credit file shows commitments the applicant did not declare",
        },
    },
    {
        "rule_id": "net_income_implausible", "framework": "individual",
        "document": {
            "requires": ["gross_annual_income", "net_to_gross_ratio"],
            "when": "gross_annual_income > 30000 and (net_to_gross_ratio > 0.95 or net_to_gross_ratio < 0.5)",
            "status": "flag",
            "message": "Take-home pay looks out of line with gross income, so the figures need checking",
        },
    },
    {
        "rule_id": "purpose_excluded", "framework": "individual",
        "document": {
            "requires": ["purpose_eligibility"], "when": "purpose_eligibility == 'excluded'",
            "status": "fail", "message": "The bank does not lend for this purpose on this product",
        },
    },
    {
        "rule_id": "purpose_not_suited", "framework": "individual",
        "document": {
            "requires": ["purpose_eligibility"], "when": "purpose_eligibility == 'not_suited_to_product'",
            "status": "flag", "message": "The stated purpose does not match what this product is for",
        },
    },
    {
        "rule_id": "purpose_needs_detail", "framework": "individual",
        "document": {
            "requires": ["purpose_eligibility"], "when": "purpose_eligibility == 'needs_detail'",
            "status": "flag", "message": "The purpose is 'other', so the specific use of funds needs to be confirmed",
        },
    },
    {
        "rule_id": "product_limits_breached", "framework": "individual",
        "document": {
            "requires": ["product_limit_breaches"], "when": "product_limit_breaches > 0",
            "status": "fail", "message": "The amount or term requested is outside what this product allows",
        },
    },
    {
        "rule_id": "visa_expires_before_term_end", "framework": "individual",
        "document": {
            "requires": ["visa_shortfall_months"], "when": "visa_shortfall_months > 0",
            "status": "flag", "message": "The applicant's visa expires before the end of the loan term",
        },
    },
    {
        "rule_id": "age_at_maturity_high", "framework": "individual",
        "document": {
            "requires": ["age_at_maturity", "max_age_at_maturity"], "when": "age_at_maturity > max_age_at_maturity",
            "status": "flag", "message": "The applicant will be over the policy age when the loan ends, so an exit strategy is needed",
        },
    },
    {
        "rule_id": "vehicle_too_old", "framework": "individual",
        "document": {
            "requires": ["vehicle_age_assessed", "vehicle_age_limit"], "when": "vehicle_age_assessed > vehicle_age_limit",
            "status": "fail", "message": "The vehicle is older than this product allows",
        },
    },
    {
        "rule_id": "balloon_above_limit", "framework": "individual",
        "document": {
            "requires": ["balloon_pct", "max_balloon_pct"], "when": "balloon_pct > max_balloon_pct",
            "status": "flag", "message": "The balloon payment is above the bank's maximum",
        },
    },
    {
        "rule_id": "non_standard_repayment", "framework": "individual",
        "document": {
            "requires": ["repayment_structure"], "when": "repayment_structure != 'principal_and_interest'",
            "status": "flag", "message": "Interest-only or balloon repayments, so suitability must be documented",
        },
    },
    {
        "rule_id": "stressed_nsr_low", "framework": "individual",
        "document": {
            "requires": ["stressed_nsr"], "when": "stressed_nsr < 1.0",
            "status": "flag", "message": "Repayments would not be covered if the applicant's income fell",
        },
    },
    {
        "rule_id": "employment_ineligible", "framework": "individual",
        "document": {
            "requires": ["employment_stability"], "when": "employment_stability == 'ineligible'",
            "status": "fail", "message": "The applicant has no employment income to service the loan",
        },
    },
    {
        "rule_id": "employment_review", "framework": "individual",
        "document": {
            "requires": ["employment_stability"], "when": "employment_stability == 'review'",
            "status": "flag", "message": "Short time in the role, on probation, or retired, so income stability needs review",
        },
    },
    {
        "rule_id": "industry_high_risk", "framework": "individual",
        "document": {
            "requires": ["industry_sector_risk"], "when": "industry_sector_risk == 'high'",
            "status": "flag", "message": "The applicant works in an industry the bank treats as higher risk",
        },
    },
]


async def seed_rules():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        existing = set((await session.execute(
            select(Rule.rule_id).where(Rule.bank_id == DEFAULT_BANK_ID)
        )).scalars())
        added = [r for r in RULES if r["rule_id"] not in existing]
        for r in added:
            session.add(Rule(bank_id=DEFAULT_BANK_ID, **r))
        await session.commit()

    print(f"Rules seeded: {len(added)} added, {len(RULES) - len(added)} already present.")


if __name__ == "__main__":
    asyncio.run(seed_rules())