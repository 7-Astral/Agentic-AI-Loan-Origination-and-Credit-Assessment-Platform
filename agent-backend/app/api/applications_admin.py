from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ApplicationListOut, ApplicationSummaryOut
from app.core.db import get_session
from app.models.application import Application, AssessmentResult

router = APIRouter(prefix="/api/v1/applications", tags=["applications"])


@router.get("", response_model=ApplicationListOut)
async def list_applications(
    bank_id: str = Query(...),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session),
) -> ApplicationListOut:
    total = await db.scalar(
        select(func.count()).select_from(Application).where(Application.bank_id == bank_id)
    )

    stmt = (
        select(Application)
        .where(Application.bank_id == bank_id)
        .order_by(Application.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    applications = (await db.execute(stmt)).scalars().all()

    summaries: list[ApplicationSummaryOut] = []
    for application in applications:
        latest = await db.execute(
            select(AssessmentResult)
            .where(AssessmentResult.application_id == application.id)
            .order_by(AssessmentResult.created_at.desc())
            .limit(1)
        )
        result = latest.scalar_one_or_none()
        summaries.append(ApplicationSummaryOut(
            session_id=str(application.id),
            product_code=application.product_code,
            status=application.status,
            overall_score=result.overall_score if result else None,
            tier=result.tier if result else None,
            created_at=application.created_at,
        ))

    return ApplicationListOut(applications=summaries, total=total or 0)
