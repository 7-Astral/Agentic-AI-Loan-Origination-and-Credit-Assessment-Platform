from decimal import Decimal

from app.agents.assessment.retail.metrics.capacity import assess_capacity
from app.agents.assessment.retail.metrics.capital import assess_capital
from app.agents.assessment.retail.metrics.character import assess_character
from app.agents.assessment.retail.metrics.collateral import assess_collateral
from app.agents.assessment.retail.metrics.conditions import assess_conditions
from app.agents.assessment.rules.engine import evaluate, route
from app.services.core_banking import core_banking
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
        .where(Document.session_id == session_id, Document.verification_type == "bank_statements")
        .order_by(Document.uploaded_at.desc())
    )
    result = await db.execute(stmt)
    extraction = result.scalars().first()
    if extraction is None:
        return None
    return extraction.extracted_fields.get("transactions")

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

    product = await core_banking.get_product(product_code)
    policy = {
        "shading_rates": (await core_banking.get_policy("shading_rates"))["document"],
        "hem_benchmarks": (await core_banking.get_policy("hem_benchmarks"))["document"],
        "assessment_rate_buffer": (await core_banking.get_policy("assessment_rate_buffer"))["document"],
        "industry_risk": {},
    }

    metrics = {}
    metrics.update(assess_capacity(filled, product, policy, bank_transactions))
    metrics.update(assess_conditions(filled, product, policy))
    metrics.update(assess_character(filled))
    metrics.update(assess_capital(filled, bank_transactions))
    metrics.update(assess_collateral(filled))

    rules = await core_banking.get_rules("individual")
    rule_results = evaluate(rules, metrics, "individual")
    route_result = route(rule_results)
    computed_count = sum(1 for m in metrics.values() if m.usable)

    return {
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
    }