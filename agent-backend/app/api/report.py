import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.document.reconcile import RECONCILIATION_RULES
from app.agents.document.sample_docs import SAMPLES, load_layout, sample_file
from app.core.db import get_session
from app.core.service_auth import require_service_api_key
from app.models.application import Application, ApplicationSlot, AssessmentResult, Decision, Message
from app.models.documents import Document, DocumentExtraction, VerificationResult
from app.services.core_banking import core_banking
from app.services.storage import storage

router = APIRouter(
    prefix="/api/v1/applications", tags=["report"], dependencies=[Depends(require_service_api_key)]
)


def _extracted_field(verification_type: str, slot_id: str) -> str | None:
    rule = next((r for r in RECONCILIATION_RULES.get(verification_type, []) if r["slot_id"] == slot_id), None)
    return rule["extracted_field"] if rule else None



_SAMPLE_LAYOUTS = {sample_file(s).as_posix(): s for s in SAMPLES}


def _sample_layout(storage_path: str) -> dict | None:
    sample = next((s for path, s in _SAMPLE_LAYOUTS.items() if path.endswith(storage_path.replace("\\", "/"))), None)
    return load_layout(sample) if sample else None


@router.get("/{session_id}/documents/{document_id}/file")
async def get_document_file(session_id: str, document_id: str, db: AsyncSession = Depends(get_session)):
    try:
        document = await db.get(Document, uuid.UUID(document_id))
    except ValueError:
        raise HTTPException(404, "Unknown document")
    if document is None or str(document.application_id) != session_id:
        raise HTTPException(404, "Unknown document")
    try:
        content = await storage.read(document.storage_path)
    except FileNotFoundError:
        raise HTTPException(404, "Document file is no longer available")
    return Response(content=content, media_type=document.content_type)


@router.get("/{session_id}/chat-report")
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

    schema_slots: dict[str, dict] = {}
    if application.product_code:
        try:
            schema = await core_banking.get_product_requirements(application.product_code, bank_id=application.bank_id)
            schema_slots = {slot["id"]: slot for slot in schema.get("slots", [])}
        except (httpx.HTTPError, KeyError):
            schema_slots = {}
    slots = [
        {
            "slot_key": s.slot_key,
            "label": (schema_slots.get(s.slot_key) or {}).get("label"),
            "group": (schema_slots.get(s.slot_key) or {}).get("group"),
            "type": (schema_slots.get(s.slot_key) or {}).get("type"),
            "value": s.value,
            "source": s.source,
            "turn": s.turn,
        }
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
    documents_by_id = {d.id: d for d in documents_list}

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
                    "extracted_field": _extracted_field(documents_by_id[vr.document_id].verification_type, vr.slot_id),
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
                "layout": _sample_layout(d.storage_path),
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
