from typing import Any

from app.agents.assessment.metric import Channel, Metric, MetricState
from app.agents.assessment.retail import bank_analysis

CAPITAL_METRIC_NAMES = [
    "deposit_amount",
    "contribution_pct",
    "genuine_savings",
    "net_asset_position",
]


def assess_capital(filled: dict[str, Any], bank_transactions: list[dict] | None = None) -> dict[str, Metric]:
    return {
        "deposit_amount": Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.OPEN_BANKING),
        "contribution_pct": Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.OPEN_BANKING),
        "genuine_savings": bank_analysis.genuine_savings(bank_transactions),
        "net_asset_position": Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.OPEN_BANKING),
    }