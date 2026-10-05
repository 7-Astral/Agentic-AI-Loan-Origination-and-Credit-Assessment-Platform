import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy import select

from app.agents.assessment.narrative import generate_narrative, is_template
from app.agents.assessment.report_extras import assemble_report_extras
from app.agents.assessment.risk_profile import build_risk_profile
from app.agents.assessment.run import _load_policy, run_retail_assessment
from app.api.interview import _interview_config, _resolve_stage
from app.api.schemas import ApplicationReportOut
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_session
from app.core.service_auth import require_service_api_key
from app.models.application import Application, AssessmentResult
from app.services.core_banking import DEFAULT_BANK_ID, core_banking
from app.services.operational import get_filled_from_slots

router = APIRouter(prefix="/api/v1/applications", tags=["assessment"])

@router.get("/{session_id}/assessment")
async def get_assessment(request: Request, session_id: str, db: AsyncSession = Depends(get_session)):
    stage = await _resolve_stage(request, session_id)
    if stage is None:
        raise HTTPException(404, "Unknown session")
    if stage == "discovery":
        raise HTTPException(409, "No application yet — still in discovery")

    interview_graph = request.app.state.interview_graph
    try:
        result = await run_retail_assessment(interview_graph, _interview_config(session_id), db, session_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc))

    return result


async def _latest_persisted_report(db: AsyncSession, session_id: str) -> ApplicationReportOut:
    application = await db.get(Application, uuid.UUID(session_id))
    if application is None:
        raise HTTPException(404, "Unknown session")

    latest = await db.execute(
        select(AssessmentResult)
        .where(AssessmentResult.application_id == application.id)
        .order_by(AssessmentResult.created_at.desc())
        .limit(1)
    )
    result = latest.scalar_one_or_none()
    if result is None:
        raise HTTPException(409, "No assessment available for this application yet")

    product: dict = {}
    if application.product_code:
        try:
            product = await core_banking.get_product(application.product_code, bank_id=application.bank_id)
        except Exception:
            product = {}

    metrics = result.metrics or {}
    filled = await get_filled_from_slots(db, application.id)
    nsr_minimum = await _load_policy("nsr_minimum", application.bank_id)
    extras = await assemble_report_extras(
        db, application.id, application.bank_id, application.product_code,
        product, {"nsr_minimum": nsr_minimum}, metrics, filled,
    )

    narrative_summary = result.narrative_summary
    if not narrative_summary or is_template(narrative_summary):
        narrative_summary = None

    risk_profile = build_risk_profile(
        result.rule_results or [], metrics, filled, result.data_completeness or {},
    )

    return ApplicationReportOut(
        session_id=session_id,
        bank_id=application.bank_id,
        product_code=application.product_code or "",
        product_name=product.get("name"),
        status=application.status,
        generated_at=result.created_at,
        group_scores=result.group_scores or {},
        overall_score=result.overall_score,
        weights_applied=result.weights_applied or {},
        score_bands_applied=result.score_bands_applied or {},
        tier=result.tier or "underwriter_review",
        data_completeness=result.data_completeness or {},
        conditions_of_approval=result.conditions_of_approval or [],
        rule_results=result.rule_results or [],
        rule_based_indicator=result.route or {
            "tier": "underwriter_review", "fail_count": 0, "flag_count": 0, "provisional_count": 0,
        },
        metrics_computed=result.metrics_computed,
        metrics_total=result.metrics_total,
        narrative_summary=narrative_summary,
        risk_profile=risk_profile,
        **extras,
    )


@router.get(
    "/{session_id}/report",
    response_model=ApplicationReportOut,
    dependencies=[Depends(require_service_api_key)],
)
async def get_application_report(request: Request, session_id: str, db: AsyncSession = Depends(get_session)):
    stage = await _resolve_stage(request, session_id)
    if stage is None or stage == "discovery":
        return await _latest_persisted_report(db, session_id)


    application = await db.get(Application, uuid.UUID(session_id))
    if application is not None and application.platform_application_id is not None:
        return await _latest_persisted_report(db, session_id)

    interview_graph = request.app.state.interview_graph
    try:
        result = await run_retail_assessment(interview_graph, _interview_config(session_id), db, session_id)
    except ValueError:
        return await _latest_persisted_report(db, session_id)

    score_report = result["score_report"]
    route_result = result["route"]

    return ApplicationReportOut(
        session_id=session_id,
        bank_id=application.bank_id if application else DEFAULT_BANK_ID,
        product_code=result["product_code"],
        product_name=(result.get("product") or {}).get("name"),
        status=application.status if application else "assessment",
        generated_at=datetime.now(timezone.utc),
        group_scores=score_report["group_scores"],
        overall_score=score_report["overall_score"],
        weights_applied=score_report["weights_applied"],
        score_bands_applied=score_report["score_bands_applied"],
        tier=score_report["tier"],
        data_completeness=score_report["data_completeness"],
        conditions_of_approval=result["conditions_of_approval"],
        rule_results=result["rule_results"],
        rule_based_indicator=route_result,
        metrics_computed=result["metrics_computed"],
        metrics_total=result["metrics_total"],
        narrative_summary=result["narrative_summary"],
        risk_profile=result["risk_profile"],
        applicant_summary=result["applicant_summary"],
        key_figures=result["key_figures"],
        policy_comparison=result["policy_comparison"],
        bank_policy_check=result["bank_policy_check"],
        documents=result["documents"],
        verifications=result["verifications"],
        transcript=result["transcript"],
    )


@router.get("/{session_id}/report/narrative", dependencies=[Depends(require_service_api_key)])
async def get_report_narrative(session_id: str, db: AsyncSession = Depends(get_session)) -> dict:
    try:
        app_id = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(404, "Unknown session")
    latest = await db.execute(
        select(AssessmentResult)
        .where(AssessmentResult.application_id == app_id)
        .order_by(AssessmentResult.created_at.desc())
        .limit(1)
    )
    result = latest.scalar_one_or_none()
    if result is None:
        raise HTTPException(409, "No assessment available for this application yet")
    if result.narrative_summary and not is_template(result.narrative_summary):
        return {"narrative_summary": result.narrative_summary, "ai_generated": True}

    application = await db.get(Application, app_id)
    product: dict = {}
    if application is not None and application.product_code:
        try:
            product = await core_banking.get_product(application.product_code, bank_id=application.bank_id)
        except Exception:
            product = {}
    score_report = {
        "overall_score": result.overall_score, "tier": result.tier or "underwriter_review",
        "group_scores": result.group_scores or {}, "data_completeness": result.data_completeness or {},
    }
    text, ai_generated = await generate_narrative(score_report, product)
    if not ai_generated:
        return {"narrative_summary": text, "ai_generated": False}

    result.narrative_summary = text
    result.narrative_summary_score = result.overall_score
    await db.commit()
    return {"narrative_summary": text, "ai_generated": True}
