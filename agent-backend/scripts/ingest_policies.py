import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.agents.policy.ingest import ingest_policies
from app.core.db import async_session, engine


async def main() -> None:
    async with async_session() as db:
        count = await ingest_policies(db)
    await engine.dispose()
    print(f"Stored {count} policy chunks.")


if __name__ == "__main__":
    asyncio.run(main())
