from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mock_core_banking.db import get_session
from mock_core_banking.models import Rule
from mock_core_banking.routers.deps import get_bank_or_404
from mock_core_banking.schemas import RuleCreate, RuleOut, RuleUpdate

router = APIRouter(prefix="/api/v1/banks/{bank_id}/rules", tags=["admin:rules"])


def _to_out(rule: Rule) -> RuleOut:
    return RuleOut(rule_id=rule.rule_id, framework=rule.framework, **rule.document)


def _to_document(payload: RuleCreate | RuleUpdate) -> dict:
    return {
        "requires": payload.requires,
        "when": payload.when,
        "status": payload.status,
        "message": payload.message,
    }


@router.get("", response_model=list[RuleOut])
async def list_rules(bank_id: str, session: AsyncSession = Depends(get_session)):
    await get_bank_or_404(bank_id, session)
    result = await session.execute(select(Rule).where(Rule.bank_id == bank_id))
    return [_to_out(r) for r in result.scalars().all()]


@router.post("", response_model=RuleOut, status_code=201)
async def create_rule(bank_id: str, payload: RuleCreate, session: AsyncSession = Depends(get_session)):
    await get_bank_or_404(bank_id, session)

    existing = await session.execute(
        select(Rule).where(Rule.bank_id == bank_id, Rule.rule_id == payload.rule_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(409, f"Rule '{payload.rule_id}' already exists for this bank")

    rule = Rule(
        bank_id=bank_id, rule_id=payload.rule_id, framework=payload.framework,
        document=_to_document(payload),
    )
    session.add(rule)
    await session.commit()
    return _to_out(rule)


@router.put("/{rule_id}", response_model=RuleOut)
async def update_rule(
    bank_id: str, rule_id: str, payload: RuleUpdate, session: AsyncSession = Depends(get_session)
):
    await get_bank_or_404(bank_id, session)
    result = await session.execute(select(Rule).where(Rule.bank_id == bank_id, Rule.rule_id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(404, f"Rule '{rule_id}' not found for this bank")

    rule.framework = payload.framework
    rule.document = _to_document(payload)
    await session.commit()
    return _to_out(rule)


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(bank_id: str, rule_id: str, session: AsyncSession = Depends(get_session)):
    await get_bank_or_404(bank_id, session)
    result = await session.execute(select(Rule).where(Rule.bank_id == bank_id, Rule.rule_id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(404, f"Rule '{rule_id}' not found for this bank")
    await session.delete(rule)
    await session.commit()
