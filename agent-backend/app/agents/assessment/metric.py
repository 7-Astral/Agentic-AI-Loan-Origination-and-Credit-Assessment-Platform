from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class MetricState(str, Enum):
    COMPUTED = "computed"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"
    STALE = "stale"


class EvidenceTier(str, Enum):
    DECLARED = "declared"
    DOCUMENTED = "documented"
    VERIFIED = "verified"
    AUTHORITATIVE = "authoritative"


class Channel(str, Enum):
    DECLARATION = "declaration"
    DOCUMENT = "document"
    BUREAU = "bureau"
    OPEN_BANKING = "open_banking"
    REGISTRY = "registry"
    VALUATION = "valuation"
    BENCHMARK = "benchmark"
    POLICY = "policy"
    DERIVED = "derived"


@dataclass(frozen=True)
class Metric(Generic[T]):
    value: T | None
    state: MetricState
    channel: Channel
    tier: EvidenceTier | None = None
    unit: str | None = None
    artifact_ref: str | None = None
    inputs: dict[str, Any] | None = None
    variance_pct: Decimal | None = None
    confidence: Decimal | None = None
    computed_at: datetime | None = None
    policy_version: str | None = None

    @property
    def usable(self) -> bool:
        return self.state == MetricState.COMPUTED and self.value is not None


def unavailable(channel: Channel = Channel.DECLARATION) -> Metric:
    return Metric(value=None, state=MetricState.UNAVAILABLE, channel=channel)