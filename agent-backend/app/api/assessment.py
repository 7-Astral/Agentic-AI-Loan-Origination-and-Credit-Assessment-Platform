from fastapi import APIRouter, HTTPException, Request, Depends

from app.agents.assessment.run import run_retail_assessment
from app.api.interview import _interview_config, _resolve_stage
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_session

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