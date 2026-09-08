import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import LoanType
from models.prompt_template import PromptTemplate


async def _get_template(
    db: AsyncSession, bank_id: uuid.UUID | None, loan_type: LoanType | None, agent_name: str
) -> PromptTemplate | None:
    bank_filter = (
        or_(PromptTemplate.bank_id == bank_id, PromptTemplate.bank_id.is_(None))
        if bank_id is not None
        else PromptTemplate.bank_id.is_(None)
    )
    loan_type_filter = (
        PromptTemplate.loan_type == loan_type
        if loan_type is not None
        else PromptTemplate.loan_type.is_(None)
    )
    stmt = (
        select(PromptTemplate)
        .where(
            PromptTemplate.agent_name == agent_name,
            PromptTemplate.is_active.is_(True),
            bank_filter,
            loan_type_filter,
        )
        .order_by(PromptTemplate.bank_id.is_(None), PromptTemplate.version.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_system_prompt_content(
    db: AsyncSession,
    bank_id: uuid.UUID | None,
    loan_type: LoanType | None,
    agent_name: str = "loan_broker",
) -> str | None:
    """Returns the merged system prompt content for `agent_name`: the baseline template
    (loan_type IS NULL) plus a loan-type-specific "focus" fragment appended once the loan
    type is known — same baseline+specific merge shape as
    `agents.questions.loader.get_question_set`. Returns None only if no baseline template
    exists at all (caller falls back to a hardcoded default)."""
    baseline = await _get_template(db, bank_id, None, agent_name)
    if baseline is None:
        return None

    content = baseline.content
    if loan_type is not None:
        specific = await _get_template(db, bank_id, loan_type, agent_name)
        if specific is not None:
            content = f"{content}\n\n{specific.content}"
    return content
