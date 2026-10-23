import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from app.core.sync_runner import run


def _load(value, default):
    if value is None or value == "":
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


async def _interaction_extractor(message: str, v: dict) -> str:
    from app.agents.interaction.extractor import extract

    fields = _load(v.get("fields"), [])
    return json.dumps(await extract(fields, message, fields), ensure_ascii=False)


async def _advisor(message: str, v: dict) -> str:
    from app.agents.interaction.advisor import answer_question

    return await answer_question(
        message,
        _load(v.get("product"), {}),
        _load(v.get("slots"), []),
        _load(v.get("filled"), {}),
        _load(v.get("transcript"), []),
    )


async def _discovery_type(message: str, v: dict) -> str:
    from app.agents.interaction.discovery import classify_type_node

    state = {
        "transcript": [{"role": "user", "content": message}],
        "loan_types": _load(v.get("loan_types"), []),
    }
    result = await classify_type_node(state)
    return json.dumps(
        {"loan_type": result.get("loan_type"), "reply_to_question": result.get("pending_answer")},
        ensure_ascii=False,
    )


async def _categorize(message: str, v: dict) -> str:
    from app.agents.document.categorize import categorize_transactions

    transactions = _load(v.get("transactions"), [])
    result = await categorize_transactions(transactions)
    return json.dumps([t["category"] for t in result])


async def _policy(message: str, v: dict) -> str:
    from app.agents.policy.generator import generate_policy_answer
    from app.models.policy import PolicyChunk

    chunks = [
        PolicyChunk(
            bank=c.get("bank", "Demo Bank"),
            loan_type=c.get("loan_type", "personal"),
            category=c.get("category", "general"),
            content=c["content"],
            source=c.get("source", "eval"),
            data_status=c.get("data_status", "synthetic"),
        )
        for c in _load(v.get("chunks"), [])
    ]
    return await generate_policy_answer(message, chunks)


RUNNERS = {
    "interaction_extractor": _interaction_extractor,
    "advisor": _advisor,
    "discovery_type": _discovery_type,
    "categorize": _categorize,
    "policy": _policy,
}


def call_api(prompt, options, context):
    variables = (context or {}).get("vars") or {}
    config = (options or {}).get("config") or {}
    agent = variables.get("agent") or config.get("agent")
    if agent not in RUNNERS:
        return {"error": f"Unknown agent '{agent}'. Expected one of {sorted(RUNNERS)}"}
    merged = {**config, **variables}
    try:
        output = run(_traced(agent, prompt, merged))
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    return {"output": output}


async def _traced(agent: str, prompt: str, merged: dict) -> str:
    from app.core import observability

    with observability.trace(f"eval {agent}", input=prompt, tags=["eval", f"agent:{agent}"], metadata={"source": "promptfoo"}):
        output = await RUNNERS[agent](prompt, merged)
        observability.trace_io(input=prompt, output=output)
    observability.flush()
    return output
