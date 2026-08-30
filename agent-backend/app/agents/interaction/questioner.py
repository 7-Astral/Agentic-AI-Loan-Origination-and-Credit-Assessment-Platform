import json

from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.interaction.prompts import (
    GROUP_PREAMBLE,
    GROUP_RULES,
    INTERVIEWER_SYSTEM,
    REPAIR_SYSTEM,
)
from app.core.llm import as_text, get_llm


def _ask_spec(slot: dict) -> dict:
    spec = {
        "id": slot["id"],
        "label": slot["label"],
        "type": slot["type"],
        "guidance": slot["ask_hint"],
    }
    if slot.get("options"):
        spec["acceptable_answers"] = slot["options"]
    return spec


async def ask(
    batch: list[dict],
    filled: dict,
    recent_messages: list[dict] | None = None,
    repair: bool = False,
    validation_error: str | None = None,
) -> str:   
    
    group = batch[0].get("group")
    if group == "confirmation":
        already_answered = {k: str(v) for k, v in filled.items()}
    else:
        already_answered = {k: str(v)[:60] for k, v in list(filled.items())[-12:]}

    payload = {
        "fields_to_ask": [_ask_spec(s) for s in batch],
        "already_answered": {k: str(v)[:60] for k, v in list(filled.items())[-12:]},
        "recent_conversation": (recent_messages or [])[-6:],
    }
    if group in GROUP_RULES:
        payload["rules_you_must_state"] = GROUP_RULES[group]

    if validation_error:
        payload["why_the_last_answer_failed"] = validation_error

    llm = get_llm("interaction")
    resp = await llm.ainvoke(
        [
            SystemMessage(content=REPAIR_SYSTEM if repair else INTERVIEWER_SYSTEM),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ]
    )
    question = as_text(resp)
    preamble = GROUP_PREAMBLE.get(group)
    if preamble and not repair:
        question = f"{preamble}\n\n{question}"
    return question