from typing import Annotated, Any, Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents.interaction.extractor import extract
from app.agents.interaction.periods import PERIODS_PER_YEAR, convert, read_stated_amount, to_annual, to_monthly
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
    pending_question: str | None
    last_error: str | None
    repair: bool
    turn: int
    escalate: bool


async def select_node(state: InterviewState) -> dict:
    batch = next_batch(state["slots"], state.get("filled") or {})
    return {"current_batch": batch}


async def compose_question_node(state: InterviewState) -> dict:
    batch = state["current_batch"]
    question = await ask(
        batch,
        state.get("filled") or {},
        state.get("transcript") or [],
        repair=state.get("repair", False),
        validation_error=state.get("last_error"),
    )
    return {"pending_question": question}


async def ask_node(state: InterviewState) -> dict:
    batch = state["current_batch"]
    turn = state.get("turn", 0) + 1
    question = state.get("pending_question")
    if question is None:
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
        "pending_question": None,
        "transcript": [
            {"role": "assistant", "content": question},
            {"role": "user", "content": reply},
        ],
    }


def _pair_with_frequency(slot, raw, filled, new_filled, new_prov, by_id, turn):
    amount, frequency = read_stated_amount(raw)
    freq_slot_id = slot["frequency_slot"]
    known = filled.get(freq_slot_id) or new_filled.get(freq_slot_id)
    if not frequency or known == frequency:
        return amount, None
    if known in PERIODS_PER_YEAR:
        try:
            return float(convert(amount, frequency, known)), {"amount": amount, "frequency": frequency}
        except (ArithmeticError, TypeError, ValueError):
            return amount, None
    freq_slot = by_id.get(freq_slot_id)
    if freq_slot and frequency in (freq_slot.get("options") or []):
        new_filled[freq_slot_id] = frequency
        new_prov[freq_slot_id] = {"source": "extracted", "turn": turn}
    return amount, None


def _income_conflict(values: dict[str, Any]) -> str | None:
    amount = values.get("net_income_amount")
    frequency = values.get("net_income_frequency")
    gross = values.get("gross_annual_income")
    if amount is None or frequency not in PERIODS_PER_YEAR or not gross:
        return None
    net_annual = float(amount) * PERIODS_PER_YEAR[frequency]
    if net_annual <= float(gross) * 1.02:
        return None
    return (
        f"take-home of ${float(amount):,.0f} {frequency} would be about ${net_annual:,.0f} a year, "
        f"more than the ${float(gross):,.0f} gross income — confirm the take-home amount and how often it's received"
    )


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
        stated = None
        if slot.get("per_month") or slot.get("per_year"):
            amount, frequency = read_stated_amount(raw)
            basis = "monthly" if slot.get("per_month") else "annually"
            try:
                raw = float(to_monthly(amount, frequency) if basis == "monthly" else to_annual(amount, frequency))
            except (ArithmeticError, TypeError, ValueError):
                raw = amount  # let validate() report it as unreadable
            if frequency and frequency != basis:
                stated = {"amount": amount, "frequency": frequency}
        elif slot.get("frequency_slot"):
            raw, stated = _pair_with_frequency(slot, raw, filled, new_filled, new_prov, by_id, turn)
        try:
            new_filled[slot_id] = validate(slot, raw)
            new_prov[slot_id] = {"source": "extracted", "turn": turn}
            if stated:
                new_prov[slot_id]["stated"] = stated
        except ValidationError as exc:
            errors.append(f"{slot['label']}: {exc}")

    conflict = _income_conflict({**filled, **new_filled})
    if conflict:
        for sid in ("gross_annual_income", "net_income_amount", "net_income_frequency"):
            if sid in new_filled:
                new_filled.pop(sid)
                new_prov.pop(sid, None)
        errors.append(conflict)

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
    g.add_node("compose_question", compose_question_node)
    g.add_node("ask", ask_node)
    g.add_node("ingest", ingest_node)
    g.add_node("finish", finish_node)

    g.add_edge(START, "select")
    g.add_conditional_edges("select", route_after_select,
                            {"ask": "compose_question", "finish": "finish"})
    g.add_edge("compose_question", "ask")
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