from typing import Any

from app.agents.assessment.metric import Metric

FIVE_C_ORDER = ["capacity", "capital", "character", "collateral", "conditions"]


def build_conditions(
    filled: dict[str, Any], product: dict, metrics: dict[str, Metric], rule_results: list[dict]
) -> list[dict]:
    fired = {r["rule_id"] for r in rule_results if r["status"] in ("fail", "flag")}
    loan_type, category = product.get("loan_type"), product.get("category")
    purpose = filled.get("loan_purpose")
    conditions: list[dict] = []

    def add(condition_id: str, five_c: str, text: str, reason: str, blocking: bool = True) -> None:
        conditions.append({"id": condition_id, "category": five_c, "text": text, "reason": reason, "blocking": blocking})

    credit_score = metrics.get("credit_score")
    if credit_score is None or not credit_score.usable:
        add("credit_report", "character", "The applicant's consent to a credit check, and a satisfactory credit report.",
            "No credit report has been obtained yet.")
    if "undisclosed_liabilities_material" in fired:
        add("explain_undisclosed_debts", "character",
            "An explanation, with evidence, of the commitments on the credit file that were not declared.",
            "The credit file shows debts the applicant did not declare.")

    if "net_income_implausible" in fired:
        add("net_income_evidence", "capacity", "Payslips and bank statements confirming the take-home pay actually received.",
            "Declared take-home pay looks out of line with gross income, and affordability depends on it.")
    if "stressed_nsr_low" in fired:
        add("income_buffer", "capacity", "Confirmation the applicant could keep up repayments if income fell, for example savings.",
            "Repayments are not covered when income is reduced.", blocking=False)

    if "contribution_lmi_likely" in fired:
        add("lmi", "capital", "Lenders mortgage insurance arranged.", "The deposit is under 20% of the purchase price.")
    if loan_type == "home" and filled.get("deposit_amount"):
        gifted = filled.get("deposit_source") not in (None, "genuine_savings")
        add("deposit_evidence", "capital",
            "A gift letter or other evidence for the deposit funds." if gifted else "Statements showing how the deposit was saved.",
            f"The deposit source is declared as {str(filled.get('deposit_source')).replace('_', ' ')}.")

    security_value = metrics.get("security_value")
    if product.get("secured") and (security_value is None or not security_value.usable):
        add("valuation", "collateral", "An independent valuation of the security.", "The security has not been valued yet.")
    if category == "vehicle":
        add("contract_of_sale", "collateral", "A signed contract of sale or dealer invoice for the vehicle.", "The vehicle is the security.")
        add("vehicle_insurance", "collateral", "Comprehensive insurance over the vehicle, noting the bank's interest.",
            "The vehicle is the security.")
    if loan_type == "home":
        add("building_insurance", "collateral", "Building insurance over the property from settlement.", "The property is the security.")
        if purpose == "purchase_property":
            add("contract_of_sale", "collateral", "A signed contract of sale for the property.", "The loan is to purchase the property.")
    if filled.get("has_guarantor") is True:
        add("guarantor", "collateral", "The guarantor assessed, and a signed guarantee with independent legal advice.",
            "A guarantor is supporting the loan.")

    if "purpose_needs_detail" in fired:
        add("purpose_confirmation", "conditions", "Written confirmation of the specific use of the funds.", "The stated purpose is 'other'.")
    if purpose == "debt_consolidation":
        add("debt_payout", "conditions", "Existing debts paid out directly to the creditors at settlement, with payout statements.",
            "The purpose is debt consolidation.")
    if "age_at_maturity_high" in fired:
        add("exit_strategy", "conditions", "A documented plan for repaying the loan after retirement.",
            "The applicant will be over the policy age at the end of the term.")
    if filled.get("residency_status") == "temporary_visa":
        add("visa_evidence", "conditions", "Evidence of the current visa and its expiry date.", "The applicant is on a temporary visa.")
    if "employment_review" in fired:
        add("employment_confirmation", "conditions", "Confirmation of employment, such as an employer letter or verbal check.",
            "Time in the role is short or the applicant is on probation.")
    if "non_standard_repayment" in fired or "balloon_above_limit" in fired:
        add("structure_suitability", "conditions",
            "A written explanation of why an interest-only or balloon structure meets the applicant's objectives.",
            "The repayment structure is not standard principal and interest.")
    if "industry_high_risk" in fired:
        add("industry_confirmation", "conditions", "Confirmation of the stability of the applicant's employer or business.",
            "The applicant works in an industry the bank treats as higher risk.", blocking=False)

    return sorted(conditions, key=lambda c: (FIVE_C_ORDER.index(c["category"]), not c["blocking"]))
