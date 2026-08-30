"""Terminal chat with the interview agent."""
import asyncio
import sys

import httpx
from langgraph.types import Command

from app.agents.interaction.graph import build_graph, summary

PRODUCT = sys.argv[1] if len(sys.argv) > 1 else "VL-NEW-020"


async def main():
    url = f"http://127.0.0.1:9000/api/v1/products/{PRODUCT}/requirements"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            schema = resp.json()
    except httpx.ConnectError:
        print("Cannot reach the mock bank on port 9000 — is uvicorn running?")
        return
    except httpx.HTTPStatusError as exc:
        print(f"Mock bank returned {exc.response.status_code}")
        return

    graph = build_graph()
    config = {"configurable": {"thread_id": "terminal-1"}}

    state = {
        "product_code": schema["product_code"],
        "schema_version": schema["schema_version"],
        "slots": schema["slots"],
        "turn": 0,
    }

    print(f"{schema['product_code']}  {schema['slot_count']} slots  "
          f"schema {schema['schema_version']}")
    print("Type 'quit' to stop.\n")

    result = await graph.ainvoke(state, config)

    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        print(f"\nAgent: {payload['question']}\n")
        reply = input("You: ").strip()
        if reply.lower() in {"quit", "exit"}:
            break
        result = await graph.ainvoke(Command(resume=reply), config)

    final = await graph.aget_state(config)
    print("\n" + "-" * 50)
    print(summary(final.values))
    print("\nfilled:")
    for key, value in (final.values.get("filled") or {}).items():
        src = (final.values.get("provenance") or {}).get(key, {}).get("source", "?")
        print(f"  {key:<30}{value!r:<30}{src}")


if __name__ == "__main__":
    asyncio.run(main())