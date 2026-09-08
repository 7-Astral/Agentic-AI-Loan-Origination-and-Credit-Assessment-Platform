from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agents.risk_assessment.orchestrator import assess_application
from core.database import get_db
from schemas.risk_assessment import RiskAssessmentReport, RiskAssessmentRequest

router = APIRouter(prefix="/risk-assessment", tags=["risk-assessment"])


@router.post("", response_model=RiskAssessmentReport)
async def post_risk_assessment(
    body: RiskAssessmentRequest, db: AsyncSession = Depends(get_db)
) -> RiskAssessmentReport:
    return await assess_application(db, body.application, application_id=body.application_id)
