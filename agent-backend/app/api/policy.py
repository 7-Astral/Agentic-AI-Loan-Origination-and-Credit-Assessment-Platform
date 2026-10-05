from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.policy.generator import generate_policy_answer
from app.agents.policy.ingest import ingest_policies
from app.agents.policy.loader import DATA_STATUS
from app.agents.policy.retriever import list_policy_filters, retrieve_policy_chunks
from app.api.schemas import (
    PolicyAskRequest,
    PolicyAskResponse,
    PolicyFiltersOut,
    PolicyIngestResponse,
    PolicySourceOut,
)
from app.core.db import get_session
from app.core.identity import require_role

router = APIRouter(prefix="/api/v1/policies", tags=["policy-rag"])

ANY_ROLE = {"customer", "staff", "admin"}


@router.post("/ingest", response_model=PolicyIngestResponse)
async def ingest_policy_data(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_session),
) -> PolicyIngestResponse:
    require_role(authorization, {"admin"})
    try:
        count = await ingest_policies(db)
    except (FileNotFoundError, RuntimeError) as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return PolicyIngestResponse(status="success", data_type=DATA_STATUS, chunks_created=count)


@router.get("/filters", response_model=PolicyFiltersOut)
async def policy_filters(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_session),
) -> PolicyFiltersOut:
    require_role(authorization, ANY_ROLE)
    banks, loan_types = await list_policy_filters(db)
    return PolicyFiltersOut(banks=banks, loan_types=loan_types)


@router.post("/ask", response_model=PolicyAskResponse)
async def ask_policy(
    body: PolicyAskRequest,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_session),
) -> PolicyAskResponse:
    require_role(authorization, ANY_ROLE)
    chunks = await retrieve_policy_chunks(
        db=db,
        question=body.question,
        bank=body.bank,
        loan_type=body.loan_type,
        limit=body.top_k,
    )
    answer = await generate_policy_answer(body.question, chunks)

    return PolicyAskResponse(
        answer=answer,
        sources=[
            PolicySourceOut(
                bank=chunk.bank,
                loan_type=chunk.loan_type,
                category=chunk.category,
                content=chunk.content,
                source=chunk.source,
                data_status=chunk.data_status,
            )
            for chunk in chunks
        ],
    )
