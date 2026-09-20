import asyncio

from mock_core_banking.db import engine, async_session
from mock_core_banking.models import Base, Rule
from mock_core_banking.seed import DEFAULT_BANK_ID

RULES = [
    {
        "rule_id": "nsr_minimum", "framework": "individual",
        "document": {
            "requires": ["nsr"], "when": "nsr < 1.0", "status": "fail",
            "message": "Surplus doesn't cover the proposed repayment",
        },
    },
    {
        "rule_id": "nsr_comfortable", "framework": "individual",
        "document": {
            "requires": ["nsr"], "when": "nsr >= 1.0 and nsr < 1.2", "status": "flag",
            "message": "Surplus covers repayment but with limited buffer",
        },
    },
    {
        "rule_id": "dti_high", "framework": "individual",
        "document": {
            "requires": ["dti"], "when": "dti > 0.45", "status": "flag",
            "message": "Overall debt-to-income ratio is elevated",
        },
    },
    {
        "rule_id": "surplus_negative", "framework": "individual",
        "document": {
            "requires": ["monthly_surplus"], "when": "monthly_surplus < 0", "status": "fail",
            "message": "Negative monthly surplus after all commitments",
        },
    },
    {
        "rule_id": "character_required", "framework": "individual",
        "document": {
            "requires": ["credit_score"], "when": "credit_score < 0", "status": "flag",
            "message": "Credit character checks not yet available",
        },
    },
]


async def seed_rules():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        for r in RULES:
            session.add(Rule(bank_id=DEFAULT_BANK_ID, **r))
        await session.commit()

    print("Rules seeded.")


if __name__ == "__main__":
    asyncio.run(seed_rules())