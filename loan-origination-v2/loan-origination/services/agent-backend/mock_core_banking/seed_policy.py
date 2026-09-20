import asyncio

from mock_core_banking.db import engine, async_session
from mock_core_banking.models import Base, PolicySetting
from mock_core_banking.seed import DEFAULT_BANK_ID, POLICY_SETTINGS


async def seed_policy():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        for ps in POLICY_SETTINGS:
            session.add(PolicySetting(bank_id=DEFAULT_BANK_ID, **ps))
        await session.commit()

    print("Policy settings seeded.")


if __name__ == "__main__":
    asyncio.run(seed_policy())
