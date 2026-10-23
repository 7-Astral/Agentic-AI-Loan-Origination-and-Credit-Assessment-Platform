from typing import Any

from app.core import observability
from app.agents.assessment.metric import Channel, Metric, MetricState

COLLATERAL_METRIC_NAMES = [
    "security_value",
    "lvr",
    "valuation_status",
    "property_type_risk",
    "postcode_risk",
]


@observability.traced("assessment.retail.collateral")
def assess_collateral(filled: dict[str, Any]) -> dict[str, Metric]:
    return {
        name: Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.VALUATION)
        for name in COLLATERAL_METRIC_NAMES
    }