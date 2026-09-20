import asyncio

from sqlalchemy import select

from mock_core_banking.db import engine, async_session
from mock_core_banking.models import Base, PolicySetting
from mock_core_banking.seed import DEFAULT_BANK_ID, POLICY_SETTINGS


async def seed_policy():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        existing = set((await session.execute(
            select(PolicySetting.key, PolicySetting.version).where(PolicySetting.bank_id == DEFAULT_BANK_ID)
        )).all())
        added = [ps for ps in POLICY_SETTINGS if (ps["key"], ps["version"]) not in existing]
        for ps in added:
            session.add(PolicySetting(bank_id=DEFAULT_BANK_ID, **ps))
        await session.commit()

    print(f"Policy settings seeded: {len(added)} added, {len(POLICY_SETTINGS) - len(added)} already present.")


if __name__ == "__main__":
    asyncio.run(seed_policy())
