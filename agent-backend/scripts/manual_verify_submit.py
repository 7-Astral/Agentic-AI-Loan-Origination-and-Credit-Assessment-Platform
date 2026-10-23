"""One-off manual verification for Task 5's /submit bridge.

Fabricates a *completed* interview checkpoint directly (bypassing the LLM,
which this sandbox's network policy blocks from reaching Gemini) so the
data-extraction + platform-bridge-call + status-recording code in
app.api.interview.submit_application can be exercised end to end against
the real database, exactly as it runs in the app.
"""
import asyncio
import uuid

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.agents.interaction.graph import build_graph
from app.core.config import get_settings
from app.services.operational import ensure_application

SESSION_ID = str(uuid.uuid4())
BANK_ID = get_settings().platform_bank_id
APPLICANT_ID = "4f16ecbf-6d53-42d7-81a2-5e3580f4a862"  # customer@bank.com, seeded demo customer
PRODUCT_CODE = "PERSONAL-B3BDAD86"


async def main():
    await ensure_application(SESSION_ID, bank_id=BANK_ID, applicant_id=APPLICANT_ID)

    async with AsyncPostgresSaver.from_conn_string(get_settings().langgraph_db_url) as checkpointer:
        await checkpointer.setup()
        graph = build_graph(checkpointer)
        config = {"configurable": {"thread_id": f"{SESSION_ID}:interview"}}
        await graph.ainvoke(
            {
                "product_code": PRODUCT_CODE,
                "schema_version": "manual-verify",
                "slots": [],  # no slots left to ask -> select routes straight to finish -> END
                "filled": {
                    "loan_amount": 12000,
                    "loan_term_months": 24,
                    "loan_purpose": "debt_consolidation",
                    "purpose_detail": "Consolidating two credit cards",
                },
                "provenance": {},
                "turn": 0,
            },
            config,
        )
        snapshot = await graph.aget_state(config)
        print("values truthy:", bool(snapshot.values))
        print("next (empty means complete):", snapshot.next)

    print("SESSION_ID =", SESSION_ID)


if __name__ == "__main__":
    asyncio.run(main())
