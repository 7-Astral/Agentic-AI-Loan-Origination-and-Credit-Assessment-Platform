"""Terminal test of phase 0 discovery."""
import asyncio

from langgraph.types import Command

from app.agents.interaction.discovery import build_discovery_graph


async def main():
    graph = build_discovery_graph()
    config = {"configurable": {"thread_id": "discovery-test"}}

    result = await graph.ainvoke({"turn": 0}, config)

    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        print(f"\n[{payload['stage']}]")
        print(f"Agent: {payload['question']}\n")
        reply = input("You: ").strip()
        if reply.lower() in {"quit", "exit"}:
            break
        result = await graph.ainvoke(Command(resume=reply), config)

    final = await graph.aget_state(config)
    v = final.values
    print("\n" + "-" * 50)
    print(f"loan_type    {v.get('loan_type')}")
    print(f"product_code {v.get('product_code')}")
    print(f"turns        {v.get('turn')}")


if __name__ == "__main__":
    asyncio.run(main())