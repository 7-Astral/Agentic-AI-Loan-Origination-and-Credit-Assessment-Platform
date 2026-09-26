from decimal import Decimal
from typing import Any

from app.agents.assessment.metric import Metric, MetricState

FIVE_CS = ["capacity", "capital", "character", "collateral", "conditions"]

DEFAULT_METRIC_WEIGHTS: dict[str, dict[str, float]] = {
    "personal": {"capacity": 45, "character": 25, "capital": 10, "collateral": 0, "conditions": 20},
    "home": {"capacity": 35, "character": 15, "capital": 25, "collateral": 20, "conditions": 5},
    "business": {"capacity": 30, "character": 20, "capital": 15, "collateral": 20, "conditions": 15},
}

DEFAULT_SCORE_BANDS: dict[str, float] = {"auto_eligible_min": 80, "underwriter_review_min": 60}

DEFAULT_METRIC_SCORING: dict[str, dict] = {
    "nsr": {"type": "linear_higher_better", "floor": 0, "cap": 3},
    "dti": {"type": "linear_lower_better", "floor": 0, "cap": 8},
    "dsr": {"type": "linear_lower_better", "floor": 0, "cap": 1.0},
    "contribution_pct": {"type": "linear_higher_better", "floor": 0, "cap": 30},
    "net_asset_position": {"type": "linear_higher_better", "floor": -50000, "cap": 100000},
    "genuine_savings": {"type": "linear_higher_better", "floor": 0, "cap": 15000},
    "credit_score": {"type": "linear_higher_better", "floor": 0, "cap": 1200},
    "worst_rhi_24mo": {"type": "linear_lower_better", "floor": 0, "cap": 3},
    "unpaid_defaults": {"type": "linear_lower_better", "floor": 0, "cap": 3},
    "enquiry_velocity_6mo": {"type": "linear_lower_better", "floor": 0, "cap": 10},
    "bankruptcy_judgment_status": {"type": "banded", "bands": [
        {"equals": "none", "score": 100}, {"equals": "judgment", "score": 40}, {"score": 0},
    ]},
    "lvr": {"type": "linear_lower_better", "floor": 0, "cap": 110},
    "stressed_nsr": {"type": "linear_higher_better", "floor": -1, "cap": 1.5},
    "employment_stability": {"type": "banded", "bands": [
        {"equals": "stable", "score": 100}, {"equals": "review", "score": 50},
        {"equals": "ineligible", "score": 0}, {"score": 40},
    ]},
    "industry_sector_risk": {"type": "banded", "bands": [
        {"equals": "low", "score": 100}, {"equals": "medium", "score": 60},
        {"equals": "high", "score": 20}, {"score": 50},
    ]},
}

HEADLINE_METRICS: dict[str, list[str]] = {
    "capacity": ["nsr", "dti", "dsr"],
    "capital": ["contribution_pct", "net_asset_position", "genuine_savings"],
    "character": [
        "credit_score", "worst_rhi_24mo", "unpaid_defaults",
        "enquiry_velocity_6mo", "bankruptcy_judgment_status",
    ],
    "collateral": ["lvr"],
    "conditions": ["stressed_nsr", "employment_stability", "industry_sector_risk"],
}


def _to_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _linear(value: float, floor: float, cap: float, invert: bool) -> Decimal:
    if cap == floor:
        return Decimal("50")
    pct = (value - floor) / (cap - floor)
    pct = max(0.0, min(1.0, pct))
    if invert:
        pct = 1.0 - pct
    return Decimal(str(round(pct * 100, 2)))


def _banded(value: Any, bands: list[dict]) -> Decimal | None:
    for band in bands:
        if "equals" in band:
            if value == band["equals"]:
                return Decimal(str(band["score"]))
            continue
        if "max" in band:
            number = _to_number(value)
            if number is None:
                continue
            if band["max"] is None or number <= float(band["max"]):
                return Decimal(str(band["score"]))
            continue
        return Decimal(str(band["score"]))
    return None


def _boolean(value: Any, spec: dict) -> Decimal | None:
    good = spec.get("good_value", True)
    return Decimal(str(spec.get("good_score", 100))) if value == good else Decimal(str(spec.get("bad_score", 0)))


def normalize(value: Any, spec: dict) -> Decimal | None:
    kind = spec.get("type")
    if kind in ("linear_higher_better", "linear_lower_better"):
        number = _to_number(value)
        if number is None:
            return None
        return _linear(number, float(spec["floor"]), float(spec["cap"]), invert=(kind == "linear_lower_better"))
    if kind == "banded":
        return _banded(value, spec.get("bands", []))
    if kind == "boolean":
        return _boolean(value, spec)
    return None


def score_group(metrics: dict[str, Metric], headline_names: list[str], scoring_specs: dict[str, dict]) -> dict[str, Any]:
    used: list[dict] = []
    skipped: list[dict] = []
    total = Decimal("0")
    count = 0

    for name in headline_names:
        metric = metrics.get(name)
        spec = scoring_specs.get(name)
        if metric is None or spec is None:
            continue
        if not metric.usable:
            skipped.append({"metric": name, "reason": metric.state.value})
            continue

        normalized = normalize(metric.value, spec)
        if normalized is None:
            skipped.append({"metric": name, "reason": "not_scoreable"})
            continue

        raw = metric.value if isinstance(metric.value, str) else _to_number(metric.value)
        used.append({
            "metric": name, "raw_value": raw, "unit": metric.unit,
            "channel": metric.channel.value if metric.channel else None,
            "normalized_score": float(normalized),
        })
        total += normalized
        count += 1

    if count == 0:
        all_not_applicable = bool(skipped) and all(s["reason"] == MetricState.NOT_APPLICABLE.value for s in skipped)
        state = "not_applicable" if all_not_applicable else "unavailable"
        return {"score": None, "state": state, "metrics_used": [], "metrics_skipped": skipped}

    score = (total / count).quantize(Decimal("0.1"))
    return {"score": float(score), "state": "computed", "metrics_used": used, "metrics_skipped": skipped}


def compute_overall(group_results: dict[str, dict], weights: dict[str, float], score_bands: dict[str, float]) -> dict[str, Any]:
    available = {c: w for c, w in weights.items() if group_results.get(c, {}).get("state") == "computed" and w > 0}
    weight_sum = sum(available.values())

    if weight_sum <= 0:
        return {"overall_score": None, "weights_applied": {}, "tier": "underwriter_review"}

    weighted_total = sum(Decimal(str(group_results[c]["score"])) * Decimal(str(w)) for c, w in available.items())
    overall = float((weighted_total / Decimal(str(weight_sum))).quantize(Decimal("0.1")))
    weights_applied = {c: round(w / weight_sum * 100, 1) for c, w in available.items()}

    auto_min = score_bands.get("auto_eligible_min", 80)
    review_min = score_bands.get("underwriter_review_min", 60)
    if overall >= auto_min:
        tier = "auto_eligible"
    elif overall >= review_min:
        tier = "underwriter_review"
    else:
        tier = "decline_recommended"

    return {"overall_score": overall, "weights_applied": weights_applied, "tier": tier}


def build_score_report(
    groups: dict[str, dict[str, Metric]],
    weights: dict[str, float],
    score_bands: dict[str, float],
    scoring_specs: dict[str, dict],
) -> dict[str, Any]:
    group_results = {c: score_group(groups.get(c, {}), HEADLINE_METRICS[c], scoring_specs) for c in FIVE_CS}
    overall = compute_overall(group_results, weights, score_bands)

    data_completeness = {
        c: ("not_applicable" if r["state"] == "not_applicable" else "not_assessed")
        for c, r in group_results.items() if r["state"] != "computed"
    }

    return {
        "group_scores": group_results,
        "overall_score": overall["overall_score"],
        "weights_applied": overall["weights_applied"],
        "score_bands_applied": score_bands,
        "tier": overall["tier"],
        "data_completeness": data_completeness,
    }
