from typing import Annotated, Any, Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents.interaction.extractor import extract
from app.agents.interaction.questioner import ask
from app.agents.interaction.resolver import commit, next_batch, progress
from app.agents.interaction.validation import ValidationError, validate

MAX_ATTEMPTS = 3


def _merge(left: dict | None, right: dict | None) -> dict:
    return {**(left or {}), **(right or {})}


def _append(left: list | None, right: list | None) -> list:
    return (left or []) + (right or [])


class InterviewState(TypedDict, total=False):
    product_code: str
    schema_version: str
    slots: list[dict]

    transcript: Annotated[list[dict], _append]
    filled: Annotated[dict[str, Any], _merge]
    provenance: Annotated[dict[str, dict], _merge]
    attempts: Annotated[dict[str, int], _merge]

    current_batch: list[dict]
    last_error: str | None
    repair: bool
    turn: int
    escalate: bool


async def select_node(state: InterviewState) -> dict:
    batch = next_batch(state["slots"], state.get("filled") or {})
    return {"current_batch": batch}


async def ask_node(state: InterviewState) -> dict:
    batch = state["current_batch"]
    turn = state.get("turn", 0) + 1

    question = await ask(
        batch,
        state.get("filled") or {},
        state.get("transcript") or [],
        repair=state.get("repair", False),
        validation_error=state.get("last_error"),
    )

    reply = interrupt({"question": question, "turn": turn})

    return {
        "turn": turn,
        "transcript": [
            {"role": "assistant", "content": question},
            {"role": "user", "content": reply},
        ],
    }


async def ingest_node(state: InterviewState) -> dict:
    batch = state["current_batch"]
    reply = state["transcript"][-1]["content"]
    turn = state.get("turn", 0)
    filled = state.get("filled") or {}

    result = await extract(batch, reply, state["slots"])
    by_id = {s["id"]: s for s in state["slots"]}

    new_filled: dict[str, Any] = {}
    new_prov: dict[str, dict] = {}
    errors: list[str] = []

    for slot_id, raw in (result.get("values") or {}).items():
        slot = by_id.get(slot_id)
        if slot is None or slot_id in filled:
            continue
        try:
            new_filled[slot_id] = validate(slot, raw)
            new_prov[slot_id] = {"source": "extracted", "turn": turn}
        except ValidationError as exc:
            errors.append(f"{slot['label']}: {exc}")

    asked_ids = [s["id"] for s in batch]
    got_something = any(sid in new_filled for sid in asked_ids)

    attempts: dict[str, int] = {}
    if not got_something:
        for sid in asked_ids:
            attempts[sid] = (state.get("attempts") or {}).get(sid, 0) + 1

    escalate = any(v >= MAX_ATTEMPTS for v in attempts.values())
    note = result.get("notes") or ""
    error_text = "; ".join(errors) or (note if not got_something else None)

    return {
        "filled": new_filled,
        "provenance": new_prov,
        "attempts": attempts,
        "last_error": error_text,
        "repair": not got_something,
        "escalate": escalate,
    }


async def finish_node(state: InterviewState) -> dict:
    return {"current_batch": []}


def route_after_select(state: InterviewState) -> Literal["ask", "finish"]:
    return "ask" if state.get("current_batch") else "finish"


def route_after_ingest(state: InterviewState) -> Literal["select", "finish"]:
    return "finish" if state.get("escalate") else "select"


def build_graph(checkpointer=None):
    g = StateGraph(InterviewState)
    g.add_node("select", select_node)
    g.add_node("ask", ask_node)
    g.add_node("ingest", ingest_node)
    g.add_node("finish", finish_node)

    g.add_edge(START, "select")
    g.add_conditional_edges("select", route_after_select,
                            {"ask": "ask", "finish": "finish"})
    g.add_edge("ask", "ingest")
    g.add_conditional_edges("ingest", route_after_ingest,
                            {"select": "select", "finish": "finish"})
    g.add_edge("finish", END)

    return g.compile(checkpointer=checkpointer or MemorySaver())


def summary(state: InterviewState) -> dict:
    return {
        "product_code": state.get("product_code"),
        "schema_version": state.get("schema_version"),
        "turns": state.get("turn", 0),
        "escalated": state.get("escalate", False),
        **progress(state["slots"], state.get("filled") or {}),
    }