from typing import Any

HIGH = "high"
MEDIUM = "medium"
LOW = "low"


def _humanize_rule_id(rule_id: str) -> str:
    return rule_id.replace("_", " ").capitalize()


def _metric_value(metrics: dict[str, Any], name: str) -> Any:
    entry = metrics.get(name)
    if not entry or entry.get("state") != "computed":
        return None
    return entry.get("value")


def build_risk_profile(
    rule_results: list[dict],
    metrics: dict[str, Any],
    filled: dict[str, Any],
    data_completeness: dict[str, str],
) -> dict[str, Any]:
    factors: list[dict] = []

    for r in rule_results:
        if r["status"] == "fail":
            factors.append({
                "severity": HIGH, "label": _humanize_rule_id(r["rule_id"]),
                "detail": r.get("message") or "Hard policy rule triggered.",
            })
        elif r["status"] == "flag":
            factors.append({
                "severity": MEDIUM, "label": _humanize_rule_id(r["rule_id"]),
                "detail": r.get("message") or "Policy flag triggered.",
            })

    dti = _metric_value(metrics, "dti")
    if dti is not None and dti > 6:
        factors.append({
            "severity": MEDIUM, "label": "High debt-to-income",
            "detail": f"DTI is {dti}, above the common 6x high-DTI guideline.",
        })

    stressed_nsr = _metric_value(metrics, "stressed_nsr")
    if stressed_nsr is not None and stressed_nsr < 0:
        factors.append({
            "severity": HIGH, "label": "Fails under income stress",
            "detail": f"Stressed net surplus ratio is {stressed_nsr} — repayments aren't "
                      f"covered if income fell by the policy shock percentage.",
        })

    industry_risk = _metric_value(metrics, "industry_sector_risk")
    if industry_risk == "high":
        factors.append({
            "severity": MEDIUM, "label": "Higher-risk industry",
            "detail": "The applicant's employer is in an industry this lender treats as higher risk.",
        })

    dscr = _metric_value(metrics, "dscr")
    if dscr is not None and dscr < 1.25:
        factors.append({
            "severity": HIGH, "label": "Debt service cover below policy",
            "detail": f"DSCR is {dscr}x, below the usual 1.25x-1.50x target for business lending.",
        })

    concentration = _metric_value(metrics, "industry_concentration_status")
    if concentration == "restricted":
        factors.append({
            "severity": HIGH, "label": "Sector concentration restricted",
            "detail": "The bank's internal policy currently restricts new lending in this industry sector.",
        })

    deposit_source = filled.get("deposit_source")
    if deposit_source and deposit_source != "genuine_savings":
        factors.append({
            "severity": LOW, "label": "Deposit not from genuine savings",
            "detail": f"Deposit source is declared as {str(deposit_source).replace('_', ' ')}, "
                      f"which needs different evidence than a savings history.",
        })

    for group, reason in data_completeness.items():
        if reason == "not_assessed":
            factors.append({
                "severity": LOW, "label": f"{group.capitalize()} not assessed",
                "detail": "Not enough evidence was available to score this part of the application yet.",
            })

    high_count = sum(1 for f in factors if f["severity"] == HIGH)
    medium_count = sum(1 for f in factors if f["severity"] == MEDIUM)
    if high_count >= 1:
        category = HIGH
    elif medium_count >= 1:
        category = MEDIUM
    else:
        category = LOW

    return {"category": category, "factors": factors}
