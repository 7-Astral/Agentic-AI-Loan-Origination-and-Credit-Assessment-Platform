import uuid
from decimal import Decimal

import httpx

from app.agents.assessment.retail.metrics.capacity import assess_capacity
from app.agents.assessment.retail.metrics.capital import assess_capital
from app.agents.assessment.retail.metrics.character import assess_character
from app.agents.assessment.retail.metrics.collateral import assess_collateral
from app.agents.assessment.retail.metrics.conditions import DEFAULT_CONDITIONS_POLICY, assess_conditions
from app.agents.assessment.retail.approval_conditions import build_conditions
from app.agents.assessment.rules.engine import evaluate, route
from app.services.bureau import get_credit_report
from app.services.core_banking import core_banking
from app.services.operational import get_bank_id, record_assessment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.documents import Document, DocumentExtraction

def _serialise(value):
    if isinstance(value, Decimal):
        return float(value)
    return value

async def _get_bank_transactions(db: AsyncSession, session_id: str) -> list[dict] | None:
    stmt = (
        select(DocumentExtraction)
        .join(Document, Document.id == DocumentExtraction.document_id)
        .where(Document.application_id == uuid.UUID(session_id), Document.verification_type == "bank_statements")
        .order_by(Document.uploaded_at.desc())
    )
    result = await db.execute(stmt)
    extraction = result.scalars().first()
    if extraction is None:
        return None
    return extraction.extracted_fields.get("transactions")

POLICY_KEYS = ("shading_rates", "hem_benchmarks", "assessment_rate_buffer", "conditions")


async def _load_policy(key: str, bank_id: str) -> dict:
    try:
        return (await core_banking.get_policy(key, bank_id=bank_id))["document"]
    except httpx.HTTPStatusError as exc:
        if key == "conditions" and exc.response.status_code == 404:
            return DEFAULT_CONDITIONS_POLICY
        raise


async def compute_assessment(
    filled: dict,
    product_code: str,
    *,
    bank_id: str,
    bank_transactions: list[dict] | None = None,
    bureau_report: dict | None = None,
    policy_overrides: dict[str, dict] | None = None,
) -> dict:
    product = await core_banking.get_product(product_code, bank_id=bank_id)
    policy = {key: await _load_policy(key, bank_id) for key in POLICY_KEYS}
    for key, override in (policy_overrides or {}).items():
        if key not in POLICY_KEYS:
            raise ValueError(f"Unknown policy '{key}'. Expected one of {list(POLICY_KEYS)}")
        policy[key] = {**policy[key], **override}

    capacity = assess_capacity(filled, product, policy, bank_transactions)
    groups = {
        "capacity": capacity,
        "conditions": assess_conditions(filled, product, policy, capacity),
        "character": assess_character(filled, bureau_report),
        "capital": assess_capital(filled, product, bank_transactions),
        "collateral": assess_collateral(filled),
    }
    metrics = {name: m for group in groups.values() for name, m in group.items()}

    rules = await core_banking.get_rules("individual", bank_id=bank_id)
    rule_results = evaluate(rules, metrics, "individual")
    route_result = route(rule_results)
    # A recommended decline is not conditionally approved, so it carries no conditions of approval.
    conditions_of_approval = (
        [] if route_result["tier"] == "decline_recommended" else build_conditions(filled, product, metrics, rule_results)
    )
    return {
        "product": product,
        "groups": groups,
        "metrics": metrics,
        "rule_results": rule_results,
        "route": route_result,
        "conditions_of_approval": conditions_of_approval,
    }


async def run_retail_assessment(interview_graph, interview_config: dict, db: AsyncSession, session_id: str) -> dict:
    snapshot = await interview_graph.aget_state(interview_config)
    values = snapshot.values

    filled = values.get("filled") or {}
    if not filled:
        raise ValueError("No interview data available for this session yet")

    product_code = values.get("product_code")
    if not product_code:
        raise ValueError("Session has no product on file")

    # session_id = interview_config["configurable"]["thread_id"]
    bank_transactions = await _get_bank_transactions(db, session_id)
    bank_id = await get_bank_id(session_id)
    bureau_report = await get_credit_report(filled)

    assessment = await compute_assessment(
        filled, product_code, bank_id=bank_id, bank_transactions=bank_transactions, bureau_report=bureau_report
    )
    metrics = assessment["metrics"]
    rule_results = assessment["rule_results"]
    route_result = assessment["route"]
    computed_count = sum(1 for m in metrics.values() if m.usable)

    response = {
        "session_id": session_id,
        "product_code": product_code,
        "metrics": {
            name: {"state": m.state.value, "value": _serialise(m.value), "unit": m.unit}
            for name, m in metrics.items()
        },
        "metrics_computed": computed_count,
        "metrics_total": len(metrics),
        "rule_results": rule_results,
        "route": route_result,
        "conditions_of_approval": assessment["conditions_of_approval"],
    }
    await record_assessment(session_id, product_code, response)
    return response