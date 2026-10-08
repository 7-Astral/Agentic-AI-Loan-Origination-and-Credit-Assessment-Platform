from typing import Any

from app.agents.assessment.metric import Metric

FIVE_C_ORDER = ["capacity", "capital", "character", "collateral", "conditions"]

DSCR_COVENANT_MINIMUM = "1.25x"


def build_business_conditions(
    filled: dict[str, Any], product: dict, metrics: dict[str, Metric], rule_results: list[dict]
) -> list[dict]:
    fired = {r["rule_id"] for r in rule_results if r["status"] in ("fail", "flag")}
    conditions: list[dict] = []

    def add(condition_id: str, five_c: str, text: str, reason: str, blocking: bool = True) -> None:
        conditions.append({"id": condition_id, "category": five_c, "text": text, "reason": reason, "blocking": blocking})

    credit_score = metrics.get("credit_score")
    if credit_score is None or not credit_score.usable:
        add("credit_report", "character",
            "The guarantor/director's consent to a credit check, and a satisfactory credit report.",
            "No credit report has been obtained yet.")

    dscr = metrics.get("dscr")
    if dscr is None or not dscr.usable:
        add("financial_statements", "capacity",
            "2-3 years of signed financial statements (profit & loss and balance sheet).",
            "Not enough financial data has been provided yet to assess debt service cover.")
    if "biz_dscr_flag" in fired:
        add("dscr_explanation", "capacity",
            "Confirmation the business can sustain repayments given the limited buffer on debt service cover.",
            "DSCR meets the policy minimum but with little headroom.", blocking=False)
    if "biz_icr_flag" in fired:
        add("icr_explanation", "capacity",
            "Confirmation the business can absorb an interest rate increase.",
            "Interest cover is thin.", blocking=False)
    if "biz_stressed_dscr_low" in fired:
        add("cash_flow_buffer", "capacity",
            "Evidence of a cash reserve or other buffer to cover repayments if trading income softened.",
            "Debt service cover would not hold up under a standard income shock.", blocking=False)
    if "biz_turnover_volatile" in fired:
        add("turnover_explanation", "capacity",
            "A written explanation for the swing in turnover between the financial years provided.",
            "Declared turnover varies materially year to year.", blocking=False)

    projected = metrics.get("projected_dscr")
    if projected is not None and projected.usable and projected.value < 1:
        add("projection_evidence", "capacity",
            "Evidence supporting the revenue growth assumptions behind this expansion, "
            "given the stress-tested projection does not cover debt service.",
            "The haircut-adjusted projected DSCR is below 1.0x.")

    if "biz_leverage_flag" in fired or "biz_leverage_high" in fired:
        add("leverage_explanation", "capital",
            "An explanation of the business's capital structure and plans, if any, to reduce leverage.",
            "Debt-to-equity is elevated.", blocking=False)
    if "biz_liquidity_flag" in fired:
        add("liquidity_explanation", "capital",
            "Confirmation of how short-term obligations will be met given the tight current ratio.",
            "Current liabilities are close to or above current assets.", blocking=False)

    security_value = metrics.get("security_value")
    if product.get("secured") and filled.get("security_offered") != "unsecured" and (
        security_value is None or not security_value.usable
    ):
        add("valuation", "collateral", "An independent valuation of the security offered.",
            "The security has not been valued yet.")
    if filled.get("director_guarantee_accepted") is True:
        add("director_guarantee", "collateral",
            "A signed personal guarantee from each director/owner, with independent legal advice.",
            "Director/owner guarantees are required for this facility.")

    entity_review = metrics.get("entity_structure_review")
    if entity_review is not None and entity_review.usable and entity_review.value == "needs_review":
        add("entity_documents", "conditions",
            "The partnership agreement, company constitution or trust deed as applicable, "
            "identifying ultimate beneficial owners and any corporate trustee or guarantee arrangements.",
            "The entity structure requires constituent documents that have not been provided.")
    if "biz_trading_history_review" in fired:
        add("trading_history_confirmation", "conditions",
            "Confirmation the business has traded continuously under this ABN for the period claimed.",
            "Time trading is short and needs review.", blocking=False)
    if "biz_tax_noncompliant" in fired:
        add("ato_payment_plan", "conditions",
            "Evidence of the ATO payment plan and a history of compliance with it.",
            "BAS/tax obligations are not currently up to date.")
    if "biz_industry_watchlist" in fired:
        add("industry_confirmation", "conditions",
            "Confirmation of the business's resilience given current conditions in its sector.",
            "The business operates in a sector the bank is watching for concentration.", blocking=False)
    if "purpose_needs_detail" in fired or "biz_purpose_needs_detail" in fired:
        add("purpose_confirmation", "conditions", "Written confirmation of the specific use of the funds.",
            "The stated purpose is 'other'.")

    # Standing servicing condition — not tied to any fired rule, always present for a
    # business facility: commercial loans are actively managed, not set-and-forget.
    add("annual_review", "conditions",
        f"Updated financial statements submitted annually; DSCR to be maintained at or above "
        f"{DSCR_COVENANT_MINIMUM}. A covenant breach may be treated as a technical default and "
        f"trigger a renegotiation of terms.",
        "Commercial facilities are subject to an annual review, unlike a set-and-forget consumer loan.",
        blocking=False)

    return sorted(conditions, key=lambda c: (FIVE_C_ORDER.index(c["category"]), not c["blocking"]))
