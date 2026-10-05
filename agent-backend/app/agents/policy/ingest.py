from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.policy.embeddings import create_embeddings
from app.agents.policy.loader import create_policy_chunks, load_policy_rows
from app.models.policy import PolicyChunk

BATCH_SIZE = 256


async def ingest_policies(db: AsyncSession) -> int:
    chunks = create_policy_chunks(load_policy_rows())
    if not chunks:
        raise RuntimeError("No policy chunks were created from the CSV.")

    await db.execute(delete(PolicyChunk))

    count = 0
    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start : start + BATCH_SIZE]
        embeddings = await create_embeddings([chunk["content"] for chunk in batch])
        if len(embeddings) != len(batch):
            raise RuntimeError("Embedding count does not match policy chunk count.")

        db.add_all(PolicyChunk(**chunk, embedding=embedding) for chunk, embedding in zip(batch, embeddings))
        count += len(batch)
        await db.flush()

    await db.commit()
    return count
