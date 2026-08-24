from collections.abc import AsyncGenerator

import pytest_asyncio

from core.database import engine


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_pool() -> AsyncGenerator[None, None]:
    """`TestClient` drives the ASGI app on its own event loop (a background thread's
    portal), separate from the loop tests using `AsyncSessionLocal` directly run under.
    asyncpg connections are loop-bound, so sharing one pool across both loops corrupts it.
    Disposing after every test forces fresh, loop-correct connections for the next one."""
    yield
    await engine.dispose()
