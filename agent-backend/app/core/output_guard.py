import logging
import os
import re
from functools import lru_cache
from typing import Any

os.environ.setdefault("GUARDRAILS_RUN_SYNC", "true")

from guardrails import Guard, OnFailAction
from guardrails import settings as guardrails_settings
from guardrails.validator_base import FailResult, PassResult, Validator, register_validator
from pydantic import BaseModel

from app.core import observability

guardrails_settings.disable_tracing = True

logger = logging.getLogger(__name__)

OUTCOME_PATTERNS = [
    re.compile(
        r"\byou(?:'ll|'re| will| are| should| would)?(?: going to)?(?: definitely| likely| probably| certainly| almost certainly)?"
        r" (?:be |get )(?:approved|declined|rejected|accepted|knocked back)",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:guaranteed|pre-?approved|certain to be approved)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:approval|your application|the application) is (?:guaranteed|certain|likely|unlikely|assured)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:high|good|strong|great|low|poor|slim|excellent) (?:chance|chances|odds|likelihood) of (?:approval|being approved|getting approved)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\byour (?:chances|odds)(?: of approval)? (?:are|look|seem) (?:good|high|strong|great|low|slim|poor)",
        re.IGNORECASE,
    ),
]


@register_validator(name="loan/no-outcome-prediction", data_type="string")
class NoOutcomePrediction(Validator):
    def validate(self, value: Any, metadata: dict) -> PassResult | FailResult:
        for pattern in OUTCOME_PATTERNS:
            match = pattern.search(value or "")
            if match:
                return FailResult(error_message=f"Predicts the application outcome: '{match.group(0)}'")
        return PassResult()


def _configured(guard: Guard) -> Guard:
    guard.configure(allow_metrics_collection=False)
    return guard


@lru_cache(maxsize=None)
def _schema_guard(model: type[BaseModel]) -> Guard:
    return _configured(Guard.for_pydantic(model))


@lru_cache
def _customer_text_guard() -> Guard:
    return _configured(Guard().use(NoOutcomePrediction(on_fail=OnFailAction.NOOP)))


def parse_json(raw: str, model: type[BaseModel], agent: str) -> dict | None:
    try:
        outcome = _schema_guard(model).parse(raw)
    except Exception as exc:
        logger.warning("%s output failed schema validation: %s", agent, exc)
        observability.record_guardrail(f"{agent}-schema", False, {"schema": model.__name__, "error": str(exc)[:300]})
        return None
    passed = bool(outcome.validation_passed and isinstance(outcome.validated_output, dict))
    if not passed:
        logger.warning("%s output failed %s validation: %s", agent, model.__name__, outcome.error)
    observability.record_guardrail(
        f"{agent}-schema", passed, {"schema": model.__name__, "error": str(outcome.error or "")[:300]}
    )
    return outcome.validated_output if passed else None


def safe_customer_text(text: str | None, agent: str) -> str | None:
    if not text:
        return text
    outcome = _customer_text_guard().validate(text)
    errors = [
        summary.failure_reason
        for summary in (outcome.validation_summaries or [])
        if getattr(summary, "failure_reason", None)
    ]
    passed = bool(outcome.validation_passed)
    observability.record_guardrail(f"{agent}-customer-text", passed, {"errors": errors})
    if not passed:
        logger.warning("%s reply blocked by output guard: %s", agent, errors)
        return None
    return text
