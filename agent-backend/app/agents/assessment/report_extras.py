
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.policy.check import run_policy_check
from app.services import operational
from app.services.core_banking import core_banking

KEY_FIGURES = [
    ("gross_annual_income", "Gross annual income"),
    ("shaded_income", "Shaded annual income"),
    ("assessed_net_income", "Assessed net income (after shading)"),
    ("assessed_living_expenses", "Assessed living expenses"),
    ("existing_commitments", "Existing commitments"),
    ("assessment_rate", "Assessment rate (incl. buffer)"),
    ("proposed_repayment", "Proposed repayment"),
    ("monthly_surplus", "Monthly surplus"),
    ("deposit_amount", "Deposit"),
    ("contribution_pct", "Deposit contribution"),
    ("net_asset_position", "Net asset position"),
    ("genuine_savings", "Genuine savings (from bank statements)"),
    ("credit_score", "Credit score"),
]

APRA_HIGH_DTI_GUIDELINE = 6.0


def _metric_value(metrics: dict[str, Any], name: str) -> Any:
    entry = metrics.get(name)
    if not entry or entry.get("state") != "computed":
        return None
    return entry.get("value")


def build_key_figures(metrics: dict[str, Any]) -> list[dict]:
    figures = []
    for name, label in KEY_FIGURES:
        entry = metrics.get(name)
        if not entry or entry.get("state") != "computed" or entry.get("value") is None:
            continue
        figures.append({"metric": name, "label": label, "value": entry["value"], "unit": entry.get("unit")})
    return figures


def build_policy_comparison(metrics: dict[str, Any], policy: dict[str, Any], product: dict[str, Any]) -> list[dict]:
    comparisons = []

    nsr = _metric_value(metrics, "nsr")
    nsr_minimum = (policy.get("nsr_minimum") or {}).get("minimum")
    if nsr is not None and nsr_minimum is not None:
        comparisons.append({
            "metric": "nsr", "label": "Net surplus ratio", "value": nsr, "unit": "ratio",
            "threshold": nsr_minimum, "threshold_label": "Minimum required",
            "meets_threshold": nsr >= nsr_minimum,
        })

    contribution_pct = _metric_value(metrics, "contribution_pct")
    max_lvr = product.get("max_lvr")
    if contribution_pct is not None and max_lvr is not None:
        lmi_free_threshold = 100 - float(max_lvr)
        comparisons.append({
            "metric": "contribution_pct", "label": "Deposit contribution", "value": contribution_pct, "unit": "%",
            "threshold": lmi_free_threshold, "threshold_label": "Avoids LMI above this",
            "meets_threshold": contribution_pct >= lmi_free_threshold,
        })

    dti = _metric_value(metrics, "dti")
    if dti is not None:
        comparisons.append({
            "metric": "dti", "label": "Debt-to-income", "value": dti, "unit": "ratio",
            "threshold": APRA_HIGH_DTI_GUIDELINE, "threshold_label": "High-DTI guideline (not a hard policy)",
            "meets_threshold": dti <= APRA_HIGH_DTI_GUIDELINE,
        })

    stressed_nsr = _metric_value(metrics, "stressed_nsr")
    if stressed_nsr is not None:
        comparisons.append({
            "metric": "stressed_nsr", "label": "Stressed net surplus ratio", "value": stressed_nsr, "unit": "ratio",
            "threshold": 0, "threshold_label": "Must stay non-negative under income shock",
            "meets_threshold": stressed_nsr >= 0,
        })

    return comparisons


_FALLBACK_LABELS = {
    "full_name": "Full name", "date_of_birth": "Date of birth", "mobile_number": "Mobile number",
    "email_address": "Email", "residency_status": "Residency status", "employment_status": "Employment status",
    "employer_name": "Employer", "loan_amount": "Loan amount", "loan_term_months": "Loan term (months)",
    "loan_purpose": "Loan purpose", "repayment_frequency": "Repayment frequency",
}

APPLICANT_SUMMARY_KEYS = list(_FALLBACK_LABELS.keys())


def _humanize(key: str) -> str:
    return key.replace("_", " ").capitalize()


def build_applicant_summary(filled: dict[str, Any], slot_labels: dict[str, str]) -> list[dict]:
    summary = []
    for key in APPLICANT_SUMMARY_KEYS:
        if key not in filled or filled[key] in (None, ""):
            continue
        label = slot_labels.get(key) or _FALLBACK_LABELS.get(key) or _humanize(key)
        summary.append({"id": key, "label": label, "value": filled[key]})
    return summary


async def assemble_report_extras(
    db: AsyncSession,
    application_id: uuid.UUID,
    bank_id: str,
    product_code: str | None,
    product: dict[str, Any],
    policy: dict[str, Any],
    metrics: dict[str, Any],
    filled: dict[str, Any],
) -> dict[str, Any]:
    """Everything in the report besides the score itself and the narrative
    (narrative has its own caching path — see narrative.get_or_generate).
    Shared by both the live (run.py) and DB-fallback (assessment.py) report
    paths so they build these sections identically."""
    slot_labels: dict[str, str] = {}
    if product_code:
        try:
            schema = await core_banking.get_product_requirements(product_code, bank_id=bank_id)
            slot_labels = {s["id"]: s["label"] for s in schema.get("slots", [])}
        except Exception:
            slot_labels = {}

    extras = {
        "applicant_summary": build_applicant_summary(filled, slot_labels),
        "key_figures": build_key_figures(metrics),
        "policy_comparison": build_policy_comparison(metrics, policy, product),
        "documents": await operational.list_documents(db, application_id),
        "verifications": await operational.list_verifications(db, application_id),
        "transcript": await operational.list_transcript(db, application_id),
    }
    extras["bank_policy_check"] = await run_policy_check(db, product, metrics, filled)
    return extras
