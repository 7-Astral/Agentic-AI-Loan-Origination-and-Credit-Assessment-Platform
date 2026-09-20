"""Staff-facing report for a chat-originated application: everything the
interview, Five C's assessment, and document verification produced, in one
payload. Server-to-server only — called by services/api's
GET /bank/loan-applications/{id}/chat-report proxy (see require_service_api_key
in app.core.service_auth), never directly by the staff frontend, so a bank's
own staff auth/scoping stays entirely services/api's responsibility.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.service_auth import require_service_api_key
from app.models.application import Application, ApplicationSlot, AssessmentResult, Decision, Message
from app.models.documents import Document, DocumentExtraction, VerificationResult

router = APIRouter(
    prefix="/api/v1/applications", tags=["report"], dependencies=[Depends(require_service_api_key)]
)


@router.get("/{session_id}/report")
async def get_application_report(session_id: str, db: AsyncSession = Depends(get_session)):
    try:
        app_id = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(404, "Unknown session")

    application = await db.get(Application, app_id)
    if application is None:
        raise HTTPException(404, "Unknown session")

    messages_result = await db.execute(
        select(Message).where(Message.application_id == app_id).order_by(Message.id.asc())
    )
    transcript = [
        {"role": m.role, "content": m.content, "turn": m.turn, "created_at": m.created_at.isoformat()}
        for m in messages_result.scalars().all()
    ]

    slots_result = await db.execute(
        select(ApplicationSlot).where(ApplicationSlot.application_id == app_id).order_by(ApplicationSlot.slot_key)
    )
    slots = [
        {"slot_key": s.slot_key, "value": s.value, "source": s.source, "turn": s.turn}
        for s in slots_result.scalars().all()
    ]

    assessment_result = await db.execute(
        select(AssessmentResult)
        .where(AssessmentResult.application_id == app_id)
        .order_by(AssessmentResult.created_at.desc())
        .limit(1)
    )
    latest_assessment = assessment_result.scalar_one_or_none()
    assessment = (
        {
            "product_code": latest_assessment.product_code,
            "metrics": latest_assessment.metrics,
            "metrics_computed": latest_assessment.metrics_computed,
            "metrics_total": latest_assessment.metrics_total,
            "rule_results": latest_assessment.rule_results,
            "route": latest_assessment.route,
            "created_at": latest_assessment.created_at.isoformat(),
        }
        if latest_assessment
        else None
    )

    docs_result = await db.execute(
        select(Document).where(Document.application_id == app_id).order_by(Document.uploaded_at.asc())
    )
    documents_list = docs_result.scalars().all()
    doc_ids = [d.id for d in documents_list]

    extractions_by_doc: dict = {}
    if doc_ids:
        extraction_result = await db.execute(
            select(DocumentExtraction).where(DocumentExtraction.document_id.in_(doc_ids))
        )
        for ex in extraction_result.scalars().all():
            extractions_by_doc[ex.document_id] = ex

    verifications_by_doc: dict = {}
    if doc_ids:
        vr_result = await db.execute(select(VerificationResult).where(VerificationResult.document_id.in_(doc_ids)))
        for vr in vr_result.scalars().all():
            verifications_by_doc.setdefault(vr.document_id, []).append(
                {
                    "slot_id": vr.slot_id,
                    "declared_value": vr.declared_value,
                    "extracted_value": vr.extracted_value,
                    "status": vr.status,
                }
            )

    documents = []
    for d in documents_list:
        extraction = extractions_by_doc.get(d.id)
        documents.append(
            {
                "document_id": str(d.id),
                "verification_type": d.verification_type,
                "original_filename": d.original_filename,
                "content_type": d.content_type,
                "status": d.status,
                "uploaded_at": d.uploaded_at.isoformat(),
                "extraction": (
                    {"extracted_fields": extraction.extracted_fields, "notes": extraction.notes}
                    if extraction
                    else None
                ),
                "verifications": verifications_by_doc.get(d.id, []),
            }
        )

    decision_result = await db.execute(
        select(Decision).where(Decision.application_id == app_id).order_by(Decision.decided_at.desc()).limit(1)
    )
    latest_decision = decision_result.scalar_one_or_none()
    decision = (
        {
            "outcome": latest_decision.outcome,
            "reasoning": latest_decision.reasoning,
            "decided_at": latest_decision.decided_at.isoformat(),
        }
        if latest_decision
        else None
    )

    return {
        "session_id": session_id,
        "status": application.status,
        "bank_id": application.bank_id,
        "applicant_id": str(application.applicant_id) if application.applicant_id else None,
        "product_code": application.product_code,
        "platform_application_id": (
            str(application.platform_application_id) if application.platform_application_id else None
        ),
        "platform_status": application.platform_status,
        "created_at": application.created_at.isoformat(),
        "updated_at": application.updated_at.isoformat(),
        "transcript": transcript,
        "slots": slots,
        "assessment": assessment,
        "documents": documents,
        "decision": decision,
    }
