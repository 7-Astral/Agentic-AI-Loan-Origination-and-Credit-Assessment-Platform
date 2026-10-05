from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.policy.embeddings import create_query_embedding
from app.models.policy import PolicyChunk


async def retrieve_policy_chunks(
    db: AsyncSession,
    question: str,
    bank: str | None = None,
    loan_type: str | None = None,
    limit: int = 5,
) -> list[PolicyChunk]:
    query_embedding = await create_query_embedding(question)

    stmt = select(PolicyChunk)
    if bank:
        stmt = stmt.where(func.lower(PolicyChunk.bank) == bank.strip().lower())
    if loan_type:
        stmt = stmt.where(func.lower(PolicyChunk.loan_type) == loan_type.strip().lower())

    stmt = stmt.order_by(PolicyChunk.embedding.cosine_distance(query_embedding)).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_policy_filters(db: AsyncSession) -> tuple[list[str], list[str]]:
    banks = await db.execute(select(PolicyChunk.bank).distinct().order_by(PolicyChunk.bank))
    loan_types = await db.execute(select(PolicyChunk.loan_type).distinct().order_by(PolicyChunk.loan_type))
    return list(banks.scalars().all()), list(loan_types.scalars().all())
