from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.agents.assessment.metric import Channel, Metric, MetricState
from app.agents.assessment.retail.metrics.conditions import (
    DEFAULT_CONDITIONS_POLICY,
    loan_amount_and_term,
    loan_purpose,
    product_limit_breaches,
    product_structure,
    purpose_eligibility,
    repayment_structure,
)

CONDITIONS_METRIC_NAMES = [
    "loan_purpose", "purpose_eligibility", "loan_amount_and_term", "product_limit_breaches",
    "product_structure", "repayment_structure", "trading_history_stability", "tax_compliance",
    "industry_sector_risk", "industry_concentration_status", "turnover_trend_stability",
    "stressed_dscr", "projected_dscr", "entity_structure_review",
]

# Business-specific additions to the shared conditions policy (merged with
# retail's DEFAULT_CONDITIONS_POLICY, which already carries excluded_purposes/
# expected_purposes/industry_risk shared across loan types).
DEFAULT_BUSINESS_CONDITIONS_POLICY: dict[str, Any] = {
    "min_years_trading_stable": 2,
    "min_years_trading_review": 1,
    "cash_flow_shock_pct": 15,
    "projection_haircut_pct": 25,
    "turnover_volatility_threshold_pct": 30,
    "restricted_industries": [],
    "watchlist_industries": ["construction", "accommodation_food"],
    "entity_documents_required": ("partnership", "company", "trust"),
}

ENTITY_STRUCTURES_REQUIRING_DOCS = ("partnership", "company", "trust")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _computed(value, channel: Channel, **kwargs) -> Metric:
    return Metric(value=value, state=MetricState.COMPUTED, channel=channel, computed_at=_now(), **kwargs)


def _unavailable(channel: Channel, **kwargs) -> Metric:
    return Metric(value=None, state=MetricState.UNAVAILABLE, channel=channel, **kwargs)


def trading_history_stability(filled: dict[str, Any], policy: dict) -> Metric[str]:
    years = filled.get("years_trading")
    if years is None:
        return _unavailable(Channel.DECLARATION)
    years = float(years)
    if years < policy.get("min_years_trading_review", 1):
        verdict = "ineligible"
    elif years < policy.get("min_years_trading_stable", 2):
        verdict = "review"
    else:
        verdict = "stable"
    return _computed(verdict, Channel.POLICY, inputs={"years_trading": years})


def tax_compliance(filled: dict[str, Any]) -> Metric[str]:
    current = filled.get("ato_obligations_current")
    if current is None:
        return _unavailable(Channel.DECLARATION)
    return _computed("compliant" if current else "non_compliant", Channel.DECLARATION, inputs={
        "ato_obligations_current": current,
    })


def industry_sector_risk(filled: dict[str, Any], policy: dict) -> Metric[str]:
    industry = filled.get("industry")
    if industry is None:
        return _unavailable(Channel.POLICY)
    return _computed(policy["industry_risk"].get(industry, "unclassified"), Channel.POLICY, inputs={"industry": industry})


def industry_concentration_status(filled: dict[str, Any], policy: dict) -> Metric[str]:
    industry = filled.get("industry")
    if industry is None:
        return _unavailable(Channel.POLICY)
    if industry in policy.get("restricted_industries", []):
        status = "restricted"
    elif industry in policy.get("watchlist_industries", []):
        status = "watchlist"
    else:
        status = "open"
    return _computed(status, Channel.POLICY, inputs={"industry": industry})


def turnover_trend_stability(filled: dict[str, Any], policy: dict) -> Metric[str]:
    years = [
        filled.get("annual_turnover"),
        filled.get("prior_year_annual_turnover"),
        filled.get("two_years_prior_annual_turnover"),
    ]
    declared = [Decimal(str(y)) for y in years if y is not None]
    if len(declared) < 2:
        return _unavailable(Channel.DECLARATION)

    threshold = Decimal(str(policy.get("turnover_volatility_threshold_pct", 30))) / 100
    swings = []
    for later, earlier in zip(declared, declared[1:]):
        if earlier == 0:
            continue
        swings.append(abs(later - earlier) / abs(earlier))

    volatile = any(s > threshold for s in swings)
    verdict = "volatile" if volatile else "stable"
    return _computed(verdict, Channel.DERIVED, inputs={
        "years_compared": len(declared), "max_swing_pct": float(max(swings) * 100) if swings else None,
    })


def stressed_dscr(capacity: dict[str, Metric] | None, policy: dict) -> Metric[Decimal]:
    needed = [(capacity or {}).get(name) for name in ("ebitda", "total_debt_service")]
    if not all(m is not None and m.usable for m in needed) or needed[1].value == 0:
        return _unavailable(Channel.DERIVED)

    ebitda, debt_service = needed
    shock = Decimal(str(policy.get("cash_flow_shock_pct", 15))) / 100
    stressed_ebitda = ebitda.value * (1 - shock)
    value = (stressed_ebitda / debt_service.value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.DERIVED, unit="ratio", inputs={
        "cash_flow_shock_pct": float(shock * 100), "stressed_ebitda": float(stressed_ebitda.quantize(Decimal("0.01"))),
        "total_debt_service": float(debt_service.value),
    })


def projected_dscr(filled: dict[str, Any], capacity: dict[str, Metric] | None, policy: dict) -> Metric[Decimal]:
    if filled.get("loan_purpose") != "business_expansion":
        return Metric(value=None, state=MetricState.NOT_APPLICABLE, channel=Channel.DERIVED)

    growth_pct = filled.get("projected_revenue_growth_pct")
    needed = [(capacity or {}).get(name) for name in ("ebitda", "total_debt_service")]
    if growth_pct is None or not all(m is not None and m.usable for m in needed) or needed[1].value == 0:
        return _unavailable(Channel.DERIVED)

    ebitda, debt_service = needed
    haircut = Decimal(str(policy.get("projection_haircut_pct", 25))) / 100
    effective_growth = (Decimal(str(growth_pct)) / 100) * (1 - haircut)
    projected_ebitda = ebitda.value * (1 + effective_growth)
    value = (projected_ebitda / debt_service.value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.DERIVED, unit="ratio", inputs={
        "declared_growth_pct": float(growth_pct), "projection_haircut_pct": float(haircut * 100),
        "effective_growth_pct": float(effective_growth * 100),
        "projected_ebitda": float(projected_ebitda.quantize(Decimal("0.01"))),
    })


def entity_structure_review(filled: dict[str, Any]) -> Metric[str]:
    structure = filled.get("entity_structure")
    if structure is None:
        return _unavailable(Channel.DECLARATION)

    needs_docs = structure in ENTITY_STRUCTURES_REQUIRING_DOCS
    has_docs = bool(filled.get("entity_documents_note"))
    verdict = "needs_review" if needs_docs and not has_docs else "reviewed"
    return _computed(verdict, Channel.DECLARATION, inputs={
        "entity_structure": structure, "applicant_role": filled.get("applicant_role"),
        "has_constituent_documents": has_docs,
    })


def assess_conditions(
    filled: dict[str, Any], product: dict, policy: dict, capacity: dict[str, Metric] | None = None,
) -> dict[str, Metric]:
    rules = {**DEFAULT_CONDITIONS_POLICY, **DEFAULT_BUSINESS_CONDITIONS_POLICY, **(policy.get("conditions") or {})}

    return {
        "loan_purpose": loan_purpose(filled),
        "purpose_eligibility": purpose_eligibility(filled, product, rules),
        "loan_amount_and_term": loan_amount_and_term(filled),
        "product_limit_breaches": product_limit_breaches(filled, product),
        "product_structure": product_structure(product),
        "repayment_structure": repayment_structure(filled, product),
        "trading_history_stability": trading_history_stability(filled, rules),
        "tax_compliance": tax_compliance(filled),
        "industry_sector_risk": industry_sector_risk(filled, rules),
        "industry_concentration_status": industry_concentration_status(filled, rules),
        "turnover_trend_stability": turnover_trend_stability(filled, rules),
        "stressed_dscr": stressed_dscr(capacity, rules),
        "projected_dscr": projected_dscr(filled, capacity, rules),
        "entity_structure_review": entity_structure_review(filled),
    }
