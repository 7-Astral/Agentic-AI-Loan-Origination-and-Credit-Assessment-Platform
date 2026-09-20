from typing import Any

from app.agents.assessment.metric import Channel, Metric, MetricState

COLLATERAL_METRIC_NAMES = [
    "security_value",
    "lvr",
    "valuation_status",
    "property_type_risk",
    "postcode_risk",
]


def assess_collateral(filled: dict[str, Any]) -> dict[str, Metric]:
    """Stubbed for v1 — see module docstring."""
    return {
        name: Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.VALUATION)
        for name in COLLATERAL_METRIC_NAMES
    }