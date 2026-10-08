from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.agents.assessment.metric import Channel, Metric, MetricState
from app.agents.assessment.retail.metrics.capital import net_asset_position

CAPITAL_METRIC_NAMES = ["debt_to_equity", "current_ratio", "net_asset_position"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _computed(value, channel: Channel, **kwargs) -> Metric:
    return Metric(value=value, state=MetricState.COMPUTED, channel=channel, computed_at=_now(), **kwargs)


def _amount(filled: dict[str, Any], key: str) -> Decimal | None:
    value = filled.get(key)
    if value is None:
        return None
    return Decimal(str(value))


def debt_to_equity(filled: dict[str, Any]) -> Metric[Decimal]:
    liabilities = _amount(filled, "total_business_liabilities")
    equity = _amount(filled, "total_business_equity")
    if liabilities is None or equity is None or equity <= 0:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DERIVED)
    value = (liabilities / equity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.DERIVED, unit="ratio", inputs={
        "total_business_liabilities": float(liabilities), "total_business_equity": float(equity),
    })


def current_ratio(filled: dict[str, Any]) -> Metric[Decimal]:
    assets = _amount(filled, "current_assets")
    liabilities = _amount(filled, "current_liabilities")
    if assets is None or liabilities is None or liabilities <= 0:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DERIVED)
    value = (assets / liabilities).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.DERIVED, unit="ratio", inputs={
        "current_assets": float(assets), "current_liabilities": float(liabilities),
    })


def assess_capital(filled: dict[str, Any]) -> dict[str, Metric]:
    return {
        "debt_to_equity": debt_to_equity(filled),
        "current_ratio": current_ratio(filled),
        # Guarantor/director's personal net position — same metric as retail Capital.
        "net_asset_position": net_asset_position(filled),
    }
