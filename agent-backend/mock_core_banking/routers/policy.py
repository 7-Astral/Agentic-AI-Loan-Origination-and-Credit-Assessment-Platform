from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mock_core_banking.db import get_session
from mock_core_banking.models import LoanPolicyRow, PolicyVersion
from mock_core_banking.routers.deps import get_bank_or_404
from mock_core_banking.schemas import LoanPolicyRowOut, PolicyVersionCreate, PolicyVersionOut

router = APIRouter(prefix="/api/v1/banks/{bank_id}/policy-versions", tags=["admin:policy"])


def _to_out(pv: PolicyVersion) -> PolicyVersionOut:
    return PolicyVersionOut(
        id=str(pv.id),
        version=pv.version,
        status=pv.status,
        effective_from=pv.effective_from,
        created_at=pv.created_at,
        notes=pv.notes,
        loan_policy_rows=[
            LoanPolicyRowOut.model_validate(row) for row in pv.loan_policy_rows
        ],
    )


@router.get("", response_model=list[PolicyVersionOut])
async def list_policy_versions(bank_id: str, session: AsyncSession = Depends(get_session)):
    await get_bank_or_404(bank_id, session)
    result = await session.execute(
        select(PolicyVersion)
        .where(PolicyVersion.bank_id == bank_id)
        .options(selectinload(PolicyVersion.loan_policy_rows))
        .order_by(PolicyVersion.created_at.desc())
    )
    return [_to_out(pv) for pv in result.scalars().all()]


@router.get("/{version_id}", response_model=PolicyVersionOut)
async def get_policy_version(bank_id: str, version_id: int, session: AsyncSession = Depends(get_session)):
    await get_bank_or_404(bank_id, session)
    result = await session.execute(
        select(PolicyVersion)
        .where(PolicyVersion.id == version_id)
        .options(selectinload(PolicyVersion.loan_policy_rows))
    )
    pv = result.scalar_one_or_none()
    if pv is None or pv.bank_id != bank_id:
        raise HTTPException(404, f"Policy version '{version_id}' not found for this bank")
    return _to_out(pv)


@router.post("", response_model=PolicyVersionOut, status_code=201)
async def create_policy_version(
    bank_id: str, payload: PolicyVersionCreate, session: AsyncSession = Depends(get_session)
):
    await get_bank_or_404(bank_id, session)

    dup = await session.execute(
        select(PolicyVersion).where(PolicyVersion.bank_id == bank_id, PolicyVersion.version == payload.version)
    )
    if dup.scalar_one_or_none() is not None:
        raise HTTPException(409, f"Policy version '{payload.version}' already exists for this bank")

    active = await session.execute(
        select(PolicyVersion).where(PolicyVersion.bank_id == bank_id, PolicyVersion.status == "active")
    )
    for prior in active.scalars().all():
        prior.status = "superseded"

    pv = PolicyVersion(
        bank_id=bank_id,
        version=payload.version,
        status="active",
        effective_from=payload.effective_from,
        notes=payload.notes,
        loan_policy_rows=[
            LoanPolicyRow(**row.model_dump()) for row in payload.loan_policy_rows
        ],
    )
    session.add(pv)
    await session.commit()
    await session.refresh(pv, attribute_names=["loan_policy_rows"])
    return _to_out(pv)
