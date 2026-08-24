import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.prompt_template import PromptTemplate


async def get_active_prompt_template(
    db: AsyncSession, bank_id: uuid.UUID | None, agent_name: str = "loan_broker"
) -> PromptTemplate | None:
    """Returns the active prompt template for `agent_name`, preferring one scoped to
    `bank_id` over the platform default (bank_id IS NULL), and the latest version."""
    bank_filter = (
        or_(PromptTemplate.bank_id == bank_id, PromptTemplate.bank_id.is_(None))
        if bank_id is not None
        else PromptTemplate.bank_id.is_(None)
    )
    stmt = (
        select(PromptTemplate)
        .where(
            PromptTemplate.agent_name == agent_name,
            PromptTemplate.is_active.is_(True),
            bank_filter,
        )
        .order_by(PromptTemplate.bank_id.is_(None), PromptTemplate.version.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().first()
