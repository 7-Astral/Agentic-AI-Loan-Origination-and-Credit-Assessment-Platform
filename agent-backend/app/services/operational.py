
import uuid
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session
from app.models.application import (
    DEFAULT_BANK_ID,
    STATUS_ORDER,
    Application,
    ApplicationSlot,
    AssessmentResult,
    Decision,
    Message,
)
from app.models.documents import Document, DocumentExtraction, VerificationResult

OUTCOME_STATUS = {
    "approved": "approved",
    "declined": "declined",
    "refer_to_underwriter": "underwriter_review",
    "withdrawn": "withdrawn",
}


def _advance(current: str, new: str) -> str:
    try:
        if STATUS_ORDER.index(new) > STATUS_ORDER.index(current):
            return new
    except ValueError:
        pass
    return current


async def get_bank_id(session_id: str) -> str:
    async with async_session() as db:
        application = await db.get(Application, uuid.UUID(session_id))
        return application.bank_id if application is not None else DEFAULT_BANK_ID


async def ensure_application(
    session_id: str,
    bank_id: str = DEFAULT_BANK_ID,
    status: str = "discovery",
    applicant_id: str | None = None,
) -> None:
    app_id = uuid.UUID(session_id)
    async with async_session() as db:
        existing = await db.get(Application, app_id)
        if existing is not None:
            return
        db.add(
            Application(
                id=app_id,
                bank_id=bank_id,
                status=status,
                applicant_id=uuid.UUID(applicant_id) if applicant_id else None,
            )
        )
        await db.commit()


async def latest_open_session(applicant_id: str) -> str | None:
    # Furthest-progressed session first, so an abandoned empty chat started
    # later never hides a finished interview that is still waiting on documents.
    progress = case(
        {status: rank for rank, status in enumerate(STATUS_ORDER)},
        value=Application.status,
        else_=-1,
    )
    async with async_session() as db:
        result = await db.execute(
            select(Application.id)
            .where(
                Application.applicant_id == uuid.UUID(applicant_id),
                Application.platform_application_id.is_(None),
                Application.status.notin_(("approved", "declined", "withdrawn")),
            )
            .order_by(progress.desc(), Application.updated_at.desc())
            .limit(1)
        )
        found = result.scalar_one_or_none()
        return str(found) if found else None


async def get_applicant_id(session_id: str) -> str | None:
    async with async_session() as db:
        application = await db.get(Application, uuid.UUID(session_id))
        return str(application.applicant_id) if application and application.applicant_id else None


async def is_submitted(session_id: str) -> bool:
    async with async_session() as db:
        application = await db.get(Application, uuid.UUID(session_id))
        return application is not None and application.platform_application_id is not None


PLATFORM_STATUS_TO_LOCAL = {
    "submitted": "assessment",
    "under_review": "underwriter_review",
    "approved": "approved",
    "rejected": "declined",
    "disbursed": "approved",
}


async def record_platform_submission(session_id: str, platform_application_id: str, platform_status: str) -> None:
    app_id = uuid.UUID(session_id)
    async with async_session() as db:
        application = await db.get(Application, app_id)
        if application is None:
            return
        application.platform_application_id = uuid.UUID(platform_application_id)
        application.platform_status = platform_status
        local_status = PLATFORM_STATUS_TO_LOCAL.get(platform_status)
        if local_status:
            application.status = _advance(application.status, local_status)
        await db.commit()


async def set_application_product(session_id: str, product_code: str) -> None:
    app_id = uuid.UUID(session_id)
    async with async_session() as db:
        application = await db.get(Application, app_id)
        if application is None:
            return
        application.product_code = product_code
        application.status = _advance(application.status, "interview")
        await db.commit()


async def mirror_transcript(
    session_id: str, transcript: list[dict], turn: int | None = None, offset: int = 0
) -> None:
    app_id = uuid.UUID(session_id)
    async with async_session() as db:
        existing_count = await db.scalar(
            select(func.count()).select_from(Message).where(Message.application_id == app_id)
        )
        for entry in transcript[max(existing_count - offset, 0):]:
            db.add(Message(
                application_id=app_id,
                role=entry.get("role", ""),
                content=entry.get("content", ""),
                turn=turn,
            ))
        await db.commit()


async def mirror_turn(session_id: str, values: dict[str, Any], complete: bool, transcript_offset: int = 0) -> None:
    app_id = uuid.UUID(session_id)
    filled = values.get("filled") or {}
    provenance = values.get("provenance") or {}

    await mirror_transcript(session_id, values.get("transcript") or [], values.get("turn"), offset=transcript_offset)

    async with async_session() as db:
        for slot_key, value in filled.items():
            prov = provenance.get(slot_key) or {}
            result = await db.execute(
                select(ApplicationSlot).where(
                    ApplicationSlot.application_id == app_id,
                    ApplicationSlot.slot_key == slot_key,
                )
            )
            slot = result.scalar_one_or_none()
            if slot is None:
                db.add(ApplicationSlot(
                    application_id=app_id, slot_key=slot_key, value=value,
                    source=prov.get("source"), turn=prov.get("turn"),
                ))
            else:
                slot.value = value
                slot.source = prov.get("source")
                slot.turn = prov.get("turn")

        if complete:
            application = await db.get(Application, app_id)
            if application is not None:
                application.status = _advance(application.status, "documents")

        await db.commit()


async def get_latest_assessment(db: AsyncSession, application_id: uuid.UUID) -> AssessmentResult | None:
    result = await db.execute(
        select(AssessmentResult)
        .where(AssessmentResult.application_id == application_id)
        .order_by(AssessmentResult.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def record_assessment(session_id: str, product_code: str, result: dict[str, Any]) -> None:
    app_id = uuid.UUID(session_id)
    async with async_session() as db:
        application = await db.get(Application, app_id)
        if application is None:
            application = Application(id=app_id, bank_id=DEFAULT_BANK_ID, status="discovery")
            db.add(application)
            await db.flush() 

        score_report = result.get("score_report") or {}
        db.add(AssessmentResult(
            application_id=app_id,
            product_code=product_code,
            metrics=result.get("metrics") or {},
            metrics_computed=result.get("metrics_computed", 0),
            metrics_total=result.get("metrics_total", 0),
            rule_results=result.get("rule_results"),
            route=result.get("route"),
            group_scores=score_report.get("group_scores"),
            overall_score=score_report.get("overall_score"),
            weights_applied=score_report.get("weights_applied"),
            score_bands_applied=score_report.get("score_bands_applied"),
            tier=score_report.get("tier"),
            data_completeness=score_report.get("data_completeness"),
            conditions_of_approval=result.get("conditions_of_approval"),
            narrative_summary=result.get("narrative_summary") if result.get("narrative_ai_generated") else None,
            narrative_summary_score=score_report.get("overall_score"),
        ))
        application.status = _advance(application.status, "assessment")
        await db.commit()

async def get_filled_from_slots(db: AsyncSession, application_id: uuid.UUID) -> dict[str, Any]:
    result = await db.execute(
        select(ApplicationSlot).where(ApplicationSlot.application_id == application_id)
    )
    return {row.slot_key: row.value for row in result.scalars().all()}


async def list_documents(db: AsyncSession, application_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        select(Document, DocumentExtraction)
        .outerjoin(DocumentExtraction, DocumentExtraction.document_id == Document.id)
        .where(Document.application_id == application_id)
        .order_by(Document.uploaded_at)
    )
    return [
        {
            "document_id": str(doc.id),
            "verification_type": doc.verification_type,
            "original_filename": doc.original_filename,
            "status": doc.status,
            "uploaded_at": doc.uploaded_at,
            "extracted": extraction is not None,
        }
        for doc, extraction in result.all()
    ]


async def list_verifications(db: AsyncSession, application_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        select(VerificationResult)
        .where(VerificationResult.application_id == application_id)
        .order_by(VerificationResult.checked_at)
    )
    return [
        {
            "slot_id": v.slot_id, "declared_value": v.declared_value, "extracted_value": v.extracted_value,
            "status": v.status, "checked_at": v.checked_at,
        }
        for v in result.scalars().all()
    ]


async def list_transcript(db: AsyncSession, application_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        select(Message).where(Message.application_id == application_id).order_by(Message.id)
    )
    return [
        {"role": m.role, "content": m.content, "turn": m.turn, "created_at": m.created_at}
        for m in result.scalars().all()
    ]


async def record_decision(
    session_id: str, outcome: str, reasoning: str, decided_by: uuid.UUID | None = None
) -> None:
    app_id = uuid.UUID(session_id)
    async with async_session() as db:
        db.add(Decision(
            application_id=app_id, decided_by=decided_by, outcome=outcome, reasoning=reasoning,
        ))
        application = await db.get(Application, app_id)
        if application is not None:
            new_status = OUTCOME_STATUS.get(outcome)
            if new_status:
                application.status = _advance(application.status, new_status)
        await db.commit()
