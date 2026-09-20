from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.agents.assessment.metric import Channel, Metric, MetricState
from app.agents.assessment.retail import bank_analysis

CAPITAL_METRIC_NAMES = [
    "deposit_amount",
    "contribution_pct",
    "required_contribution_pct",
    "genuine_savings",
    "net_asset_position",
]

DEPOSIT_PRICE_PAIRS = [
    ("deposit_amount", "property_price"),
    ("trade_in_or_deposit", "vehicle_purchase_price"),
]
ASSET_KEYS = ["savings_balance", "property_equity_value", "vehicles_value", "investments_value"]
LIABILITY_KEYS = ["mortgage_balance", "credit_card_balance_total", "hecs_help_balance"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _computed(value, channel: Channel, **kwargs) -> Metric:
    return Metric(value=value, state=MetricState.COMPUTED, channel=channel, computed_at=_now(), **kwargs)


def _unavailable(channel: Channel) -> Metric:
    return Metric(value=None, state=MetricState.UNAVAILABLE, channel=channel)


def _amount(filled: dict[str, Any], key: str) -> Decimal | None:
    value = filled.get(key)
    if value is None:
        return None
    return Decimal(str(value))


def _has_deposit(product: dict) -> bool:
    return product.get("loan_type") == "home" or product.get("category") == "vehicle"


def _not_applicable(channel: Channel) -> Metric:
    return Metric(value=None, state=MetricState.NOT_APPLICABLE, channel=channel)


def deposit_amount(filled: dict[str, Any], product: dict) -> Metric[Decimal]:
    if not _has_deposit(product):
        return _not_applicable(Channel.DECLARATION)
    for deposit_key, _ in DEPOSIT_PRICE_PAIRS:
        value = _amount(filled, deposit_key)
        if value is not None:
            return _computed(value, Channel.DECLARATION, unit="AUD", inputs={
                "slot": deposit_key, "deposit_source": filled.get("deposit_source"),
            })
    return _unavailable(Channel.DECLARATION)


def contribution_pct(filled: dict[str, Any], product: dict) -> Metric[Decimal]:
    if not _has_deposit(product):
        return _not_applicable(Channel.DERIVED)
    for deposit_key, price_key in DEPOSIT_PRICE_PAIRS:
        deposit = _amount(filled, deposit_key)
        price = _amount(filled, price_key)
        if deposit is None or price is None or price <= 0:
            continue
        value = (deposit / price * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return _computed(value, Channel.DERIVED, unit="%", inputs={
            "deposit": float(deposit), "purchase_price": float(price),
        })
    return _unavailable(Channel.DERIVED)


def required_contribution_pct(product: dict) -> Metric[Decimal]:
    max_lvr = product.get("max_lvr")
    if max_lvr is None:
        return _not_applicable(Channel.POLICY)
    value = (Decimal("100") - Decimal(str(max_lvr))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.POLICY, unit="%", inputs={"max_lvr": float(max_lvr)})


def net_asset_position(filled: dict[str, Any]) -> Metric[Decimal]:
    if _amount(filled, "savings_balance") is None:
        return _unavailable(Channel.DECLARATION)

    assets = {k: _amount(filled, k) or Decimal("0") for k in ASSET_KEYS}
    liabilities = {k: _amount(filled, k) or Decimal("0") for k in LIABILITY_KEYS}
    total_assets = sum(assets.values(), Decimal("0"))
    total_liabilities = sum(liabilities.values(), Decimal("0"))

    value = (total_assets - total_liabilities).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.DECLARATION, unit="AUD", inputs={
        "total_assets": float(total_assets), "total_liabilities": float(total_liabilities),
        **{k: float(v) for k, v in assets.items()},
        **{k: float(v) for k, v in liabilities.items()},
    })


def assess_capital(
    filled: dict[str, Any], product: dict, bank_transactions: list[dict] | None = None
) -> dict[str, Metric]:
    return {
        "deposit_amount": deposit_amount(filled, product),
        "contribution_pct": contribution_pct(filled, product),
        "required_contribution_pct": required_contribution_pct(product),
        "genuine_savings": bank_analysis.genuine_savings(bank_transactions),
        "net_asset_position": net_asset_position(filled),
    }
