from typing import Any

from integration.abr import AbrResult
from integration.credit_bureau import CreditBureauResult
from schemas.application import NormalizedApplication
from schemas.risk_assessment import FiveCField


def calculate_character(bureau: CreditBureauResult | None) -> FiveCField:
    """Character comes ONLY from a matched bureau report. If the bureau call wasn't made,
    failed, or didn't match, Character is `unavailable` with a null value — a score is
    never synthesised, estimated from other fields, or produced by a language model."""
    if bureau is None or not bureau.matched:
        return FiveCField(
            value=None,
            source="unavailable",
            confidence="low",
            notes="No matching credit bureau record — character cannot be assessed.",
        )

    summary = bureau.report_summary or {}
    return FiveCField(
        value={
            "score": bureau.score,
            "band": bureau.band,
            "enquiries_last_6_months": summary.get("enquiries_last_6_months"),
            "adverse_events": summary.get("adverse_events"),
            "repayment_history": summary.get("repayment_history"),
            "oldest_account_years": summary.get("oldest_account_years"),
            "accounts_open": summary.get("accounts_open"),
        },
        source="bureau-verified",
        confidence="high",
        notes=None,
    )


def calculate_capital(app: NormalizedApplication) -> FiveCField:
    """Deposit/savings and its proportion of the requested loan. Applicant-declared only —
    genuine-savings verification requires transaction-level document analysis this platform
    doesn't perform, so confidence is capped at medium."""
    deposit = app.collateral.deposit_amount
    if deposit is None:
        return FiveCField(
            value=None,
            source="unavailable",
            confidence="low",
            notes="No declared deposit or savings amount.",
        )

    proportion_of_loan = None
    if app.loan.amount is not None and app.loan.amount > 0:
        proportion_of_loan = round(float(deposit / app.loan.amount), 4)

    return FiveCField(
        value={"deposit_amount": float(deposit), "proportion_of_loan": proportion_of_loan},
        source="applicant-declared",
        confidence="medium",
        notes=(
            "Genuine-savings verification is not performed (requires transaction-level "
            "document analysis)."
        ),
    )


def calculate_collateral(app: NormalizedApplication) -> FiveCField:
    """Asset type/value and loan-to-value ratio. The estimated value is applicant-stated,
    not independently valued."""
    estimated_value = app.collateral.estimated_value
    if estimated_value is None:
        return FiveCField(
            value=None,
            source="unavailable",
            confidence="low",
            notes="No declared asset or collateral value.",
        )

    lvr = None
    if app.loan.amount is not None and estimated_value > 0:
        lvr = round(float(app.loan.amount / estimated_value), 4)

    return FiveCField(
        value={
            "asset_type": app.collateral.asset_type,
            "estimated_value": float(estimated_value),
            "lvr": lvr,
        },
        source="applicant-declared",
        confidence="medium",
        notes="Estimated value is applicant-stated, not independently valued.",
    )


def calculate_conditions(app: NormalizedApplication, abr: AbrResult | None) -> FiveCField:
    """Loan purpose and employment stability (applicant-declared), plus — for business
    applicants with an ABN — ABR-verified entity status and trading state."""
    value: dict[str, Any] = {}
    if app.loan.purpose:
        value["loan_purpose"] = app.loan.purpose
    if app.applicant.employment.status:
        value["employment_status"] = app.applicant.employment.status
    if app.applicant.employment.years_in_role is not None:
        value["years_in_role"] = app.applicant.employment.years_in_role
    if app.business.industry:
        value["industry"] = app.business.industry
    if app.business.years_trading is not None:
        value["years_trading"] = app.business.years_trading
    if app.business.employee_count is not None:
        value["employee_count"] = app.business.employee_count

    source = "applicant-declared"
    confidence = "medium" if value else "low"
    notes: list[str] = []

    if app.business.abn:
        if abr is not None and abr.found is True:
            value.update(
                {
                    "entity_name": abr.entity_name,
                    "abn_status": abr.abn_status,
                    "entity_type": abr.entity_type,
                    "gst_registered": abr.gst_registered,
                    "address_state": abr.address_state,
                }
            )
            source = "abn-verified"
            confidence = "high"
        elif abr is not None and abr.found is False:
            value["abn_status"] = "not found at ABR"
            notes.append("The declared ABN did not match a record at the ABR.")
        else:
            notes.append("ABN lookup unavailable — business status and trading state not verified.")

    if not value:
        return FiveCField(
            value=None,
            source="unavailable",
            confidence="low",
            notes="No loan purpose, employment status or verifiable business details available.",
        )

    return FiveCField(
        value=value, source=source, confidence=confidence, notes=" ".join(notes) or None
    )
