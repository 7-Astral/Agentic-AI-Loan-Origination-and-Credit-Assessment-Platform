"""Mirrors LangGraph checkpoint state and assessment/decision events out into real,
queryable SQL. The checkpoint stays the source of truth for discovery/interview control
flow — this module only ever writes a read-model alongside it, never replaces it.

Each function opens its own short-lived session (matching the existing style where
`core_banking` is a fire-and-forget singleton, not DI-threaded) so callers in the API
layer only need a one-line call, not a threaded `db` session.
"""

import uuid
from typing import Any

from sqlalchemy import func, select

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


async def get_applicant_id(session_id: str) -> str | None:
    async with async_session() as db:
        application = await db.get(Application, uuid.UUID(session_id))
        return str(application.applicant_id) if application and application.applicant_id else None


# The main platform's LoanStatus values, translated into this service's own
# STATUS_ORDER vocabulary (see app.models.application.STATUS_ORDER).
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


async def mirror_transcript(session_id: str, transcript: list[dict], turn: int | None = None) -> None:
    """Inserts only the new tail of `transcript` beyond what's already mirrored —
    the snapshot's transcript is always the full accumulated list (append-reducer)."""
    app_id = uuid.UUID(session_id)
    async with async_session() as db:
        existing_count = await db.scalar(
            select(func.count()).select_from(Message).where(Message.application_id == app_id)
        )
        for entry in transcript[existing_count:]:
            db.add(Message(
                application_id=app_id,
                role=entry.get("role", ""),
                content=entry.get("content", ""),
                turn=turn,
            ))
        await db.commit()


async def mirror_turn(session_id: str, values: dict[str, Any], complete: bool) -> None:
    app_id = uuid.UUID(session_id)
    filled = values.get("filled") or {}
    provenance = values.get("provenance") or {}

    await mirror_transcript(session_id, values.get("transcript") or [], values.get("turn"))

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


async def record_assessment(session_id: str, product_code: str, result: dict[str, Any]) -> None:
    app_id = uuid.UUID(session_id)
    async with async_session() as db:
        db.add(AssessmentResult(
            application_id=app_id,
            product_code=product_code,
            metrics=result.get("metrics") or {},
            metrics_computed=result.get("metrics_computed", 0),
            metrics_total=result.get("metrics_total", 0),
            rule_results=result.get("rule_results"),
            route=result.get("route"),
        ))
        application = await db.get(Application, app_id)
        if application is not None:
            application.status = _advance(application.status, "assessment")
        await db.commit()


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
