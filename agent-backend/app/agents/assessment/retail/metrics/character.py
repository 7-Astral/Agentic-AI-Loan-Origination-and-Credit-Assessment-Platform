from typing import Any

from app.agents.assessment.metric import Channel, Metric, MetricState

CHARACTER_METRIC_NAMES = [
    "credit_score",
    "worst_rhi_6mo",
    "worst_rhi_24mo",
    "missed_payment_count_24mo",
    "unpaid_defaults",
    "paid_defaults",
    "enquiry_velocity_6mo",
    "bankruptcy_judgment_status",
    "hardship_flags_12mo",
    "undisclosed_liabilities",
]


def assess_character(filled: dict[str, Any]) -> dict[str, Metric]:
    """No bureau integration exists yet. Every metric is honestly
    unavailable rather than guessed or defaulted."""
    return {
        name: Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.BUREAU)
        for name in CHARACTER_METRIC_NAMES
    }