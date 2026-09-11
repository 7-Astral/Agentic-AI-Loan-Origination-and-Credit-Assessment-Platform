import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import DecisionRequest, DecisionResponse
from app.core.db import get_session
from app.models.application import Application
from app.services.operational import record_decision

router = APIRouter(prefix="/api/v1/applications", tags=["decisions"])


@router.post("/{session_id}/decision", response_model=DecisionResponse)
async def post_decision(
    session_id: str, body: DecisionRequest, db: AsyncSession = Depends(get_session)
) -> DecisionResponse:
    application = await db.get(Application, uuid.UUID(session_id))
    if application is None:
        raise HTTPException(404, "Unknown session")

    await record_decision(session_id, body.outcome, body.reasoning)

    await db.refresh(application)
    return DecisionResponse(
        session_id=session_id, outcome=body.outcome, reasoning=body.reasoning, status=application.status
    )
