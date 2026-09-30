from decimal import Decimal
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.assessment.demo_profiles import PRESETS, SAMPLE_STATEMENT
from app.agents.assessment.metric import Metric
from app.agents.assessment.run import compute_assessment
from app.services.bureau import get_credit_report, list_scenarios
from app.services.core_banking import DEFAULT_BANK_ID, core_banking

router = APIRouter(prefix="/api/v1/playground", tags=["playground"])


class AssessRequest(BaseModel):
    product_code: str
    filled: dict[str, Any]
    bureau_scenario: str | None = None
    use_sample_statement: bool = False
    policy_overrides: dict[str, dict[str, Any]] | None = None


def _metric_payload(metric: Metric) -> dict:
    value = float(metric.value) if isinstance(metric.value, Decimal) else metric.value
    return {
        "state": metric.state.value,
        "value": value,
        "unit": metric.unit,
        "channel": metric.channel.value,
        "inputs": metric.inputs,
    }


def _bureau_summary(filled: dict, report: dict | None) -> dict:
    if report is not None:
        return {"status": "pulled", "scenario": report["mock"]["scenario"], "report_id": report["report_id"]}
    if not filled.get("credit_check_consent"):
        return {"status": "skipped", "reason": "Applicant has not consented to a credit check"}
    return {"status": "skipped", "reason": "Name or date of birth missing, or bureau unreachable"}


@router.get("/options")
async def options():
    try:
        products = await core_banking.assessment.list_reference_products()
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Core banking unavailable: {exc!r}")
    return {"presets": PRESETS, "products": products, "bureau_scenarios": await list_scenarios()}


@router.post("/assess")
async def assess(payload: AssessRequest):
    bureau_report = await get_credit_report(payload.filled, payload.bureau_scenario)
    try:
        product = await core_banking.assessment.get_reference_product(payload.product_code)
        result = await compute_assessment(
            payload.filled,
            payload.product_code,
            product=product,
            bank_id=DEFAULT_BANK_ID,
            bank_transactions=SAMPLE_STATEMENT if payload.use_sample_statement else None,
            bureau_report=bureau_report,
            policy_overrides=payload.policy_overrides,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(404, f"Unknown product '{payload.product_code}'")
        raise HTTPException(502, f"Core banking error: {exc!r}")
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Core banking unavailable: {exc!r}")

    metrics = result["metrics"]
    return {
        "product": result["product"],
        "route": result["route"],
        "rule_results": result["rule_results"],
        "conditions_of_approval": result["conditions_of_approval"],
        "groups": {
            group: {name: _metric_payload(m) for name, m in group_metrics.items()}
            for group, group_metrics in result["groups"].items()
        },
        "metrics_computed": sum(1 for m in metrics.values() if m.usable),
        "metrics_total": len(metrics),
        "bureau": _bureau_summary(payload.filled, bureau_report),
    }
