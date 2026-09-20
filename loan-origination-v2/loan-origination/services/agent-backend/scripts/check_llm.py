"""Smoke test: verify Gemini access and tool calling per agent role."""
import asyncio

from langchain_core.tools import tool

from app.core.config import get_settings
from app.core.llm import AGENTS, as_text, get_llm


@tool
def get_loan_products(loan_type: str) -> str:
    """Return available loan products for a given loan type."""
    return f"[stub] products for {loan_type}"


async def basic_check():
    settings = get_settings()
    for agent in AGENTS:
        model_name = settings.model_for(agent)
        llm = get_llm(agent)
        resp = await llm.ainvoke("Reply with exactly: OK")
        print(f"{agent:<12} {model_name:<24} -> {as_text(resp)[:40]}")


async def tool_check():
    llm = get_llm("interaction").bind_tools([get_loan_products])
    resp = await llm.ainvoke(
        "I want to buy a car. Use your tools to look up what loans are available."
    )
    calls = resp.tool_calls
    if calls:
        print(f"tool calling  OK -> {calls[0]['name']}({calls[0]['args']})")
    else:
        print(f"tool calling  FAILED -> model replied in text: {as_text(resp)[:120]}")


async def main():
    await basic_check()
    await tool_check()


if __name__ == "__main__":
    asyncio.run(main())