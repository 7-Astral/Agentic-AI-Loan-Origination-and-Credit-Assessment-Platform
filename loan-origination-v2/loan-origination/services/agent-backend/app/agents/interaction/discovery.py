import json
from typing import Annotated, Any, Literal, TypedDict

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.core.llm import as_text, get_llm
from app.services.core_banking import DEFAULT_BANK_ID, core_banking

CLASSIFY_TYPE_SYSTEM = """You work out what kind of loan an Australian applicant needs
from what they say.

You will be given the applicant's message and the list of loan types this
lender actually offers (code, name, description). Match their need to one of
those codes.

Return ONLY a JSON object, no markdown fences:
{"loan_type": "<code or null>", "confidence": "high"|"low", "reply_to_question": "<text or null>"}

Rules:
- Only ever return a code that appears in the loan types given. Never invent one.
- Return null with low confidence if you genuinely cannot tell. Do not guess.
- If they asked a question rather than stating a need, answer it briefly and
  factually in reply_to_question and return null for loan_type.
- Never recommend a loan type. Classify what they said, nothing more."""

CLASSIFY_CATEGORY_SYSTEM = """The applicant has already told you their loan type.
You now need to work out which subtype fits their need.

You will be given the applicant's message, the loan type they've already
chosen, and the list of valid subtypes for that loan type (code, name).
Match their need to one of those codes.

Return ONLY a JSON object, no markdown fences:
{"category": "<code or null>", "confidence": "high"|"low", "reply_to_question": "<text or null>"}

Rules:
- Only ever return a code that appears in the subtypes given. Never invent one.
- Return null with low confidence if you genuinely cannot tell. Do not guess.
- If they asked a question, answer it briefly and factually in
  reply_to_question and return null for category.
- Never recommend a subtype."""

SELECT_SYSTEM = """The applicant is choosing between the products listed.

Return ONLY a JSON object, no markdown fences:
{"product_code": "<code or null>", "reply_to_question": "<text or null>"}

- Match their reply to one of the product codes given. They may refer to a
  product by name, by position ("the first one"), or by a feature.
- Return null if they have not clearly chosen or asked something else instead.
- If they asked a question, answer it briefly and factually. Never recommend."""


def _append(left: list | None, right: list | None) -> list:
    return (left or []) + (right or [])


class DiscoveryState(TypedDict, total=False):
    bank_id: str
    transcript: Annotated[list[dict], _append]
    loan_types: list[dict]
    loan_type: str | None
    category: str | None
    products: list[dict]
    product_code: str | None
    pending_answer: str | None
    turn: int


def _parse(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {}


def _product_brief(p: dict) -> dict:
    return {
        "product_code": p["product_code"],
        "name": p["name"],
        "interest_rate": p["interest_rate"],
        "comparison_rate": p["comparison_rate"],
        "rate_type": p["rate_type"],
        "min_amount": p["min_amount"],
        "max_amount": p["max_amount"],
        "min_term_months": p["min_term_months"],
        "max_term_months": p["max_term_months"],
        "features": p.get("features") or [],
    }


def _bank_id(state: DiscoveryState) -> str:
    return state.get("bank_id") or DEFAULT_BANK_ID


def _lt_entry(state: DiscoveryState) -> dict:
    loan_type = state.get("loan_type")
    return next((t for t in state.get("loan_types") or [] if t["code"] == loan_type), {})


async def greet_node(state: DiscoveryState) -> dict:
    opening = (
        "Hello — I can help you start a loan application. "
        "To point you in the right direction, what are you hoping to do?"
    )
    reply = interrupt({"question": opening, "stage": "discovery"})
    return {
        "turn": 1,
        "transcript": [
            {"role": "assistant", "content": opening},
            {"role": "user", "content": reply},
        ],
    }


async def classify_type_node(state: DiscoveryState) -> dict:
    reply = state["transcript"][-1]["content"]
    loan_types = state.get("loan_types") or await core_banking.list_loan_types(bank_id=_bank_id(state))

    llm = get_llm("interaction")
    resp = await llm.ainvoke([
        SystemMessage(content=CLASSIFY_TYPE_SYSTEM),
        HumanMessage(content=json.dumps({
            "applicant_message": reply,
            "loan_types": [
                {"code": t["code"], "name": t["name"], "description": t["description"]}
                for t in loan_types
            ],
        }, ensure_ascii=False)),
    ])
    parsed = _parse(as_text(resp))

    valid_codes = {t["code"] for t in loan_types}
    chosen = parsed.get("loan_type")
    if chosen not in valid_codes:
        chosen = None

    return {
        "loan_types": loan_types,
        "loan_type": chosen,
        "category": None,
        "pending_answer": parsed.get("reply_to_question"),
    }


async def clarify_type_node(state: DiscoveryState) -> dict:
    turn = state.get("turn", 0) + 1
    answer = (state.get("pending_answer") or "").strip()
    loan_types = state.get("loan_types") or await core_banking.list_loan_types(bank_id=_bank_id(state))
    names = ", ".join(t["name"].lower() for t in loan_types)
    prompt = f"Is this for {names}, or something else?"
    if answer and not answer.rstrip().endswith("?"):
        question = f"{answer}\n\n{prompt}"
    else:
        question = f"I want to make sure I point you the right way. {prompt}"

    reply = interrupt({"question": question, "stage": "discovery"})
    return {
        "turn": turn,
        "loan_types": loan_types,
        "pending_answer": None,
        "transcript": [
            {"role": "assistant", "content": question},
            {"role": "user", "content": reply},
        ],
    }


async def classify_category_node(state: DiscoveryState) -> dict:
    reply = state["transcript"][-1]["content"]
    lt = _lt_entry(state)
    categories = lt.get("categories", [])

    llm = get_llm("interaction")
    resp = await llm.ainvoke([
        SystemMessage(content=CLASSIFY_CATEGORY_SYSTEM),
        HumanMessage(content=json.dumps({
            "applicant_message": reply,
            "loan_type": lt.get("name"),
            "categories": categories,
        }, ensure_ascii=False)),
    ])
    parsed = _parse(as_text(resp))

    valid_codes = {c["code"] for c in categories}
    chosen = parsed.get("category")
    if chosen not in valid_codes:
        chosen = None

    return {
        "category": chosen,
        "pending_answer": parsed.get("reply_to_question"),
    }


async def clarify_category_node(state: DiscoveryState) -> dict:
    turn = state.get("turn", 0) + 1
    answer = (state.get("pending_answer") or "").strip()
    lt = _lt_entry(state)
    names = ", ".join(c["name"].lower() for c in lt.get("categories", []))
    prompt = f"Which is it — {names}?"
    if answer and not answer.rstrip().endswith("?"):
        question = f"{answer}\n\n{prompt}"
    else:
        question = f"Just to narrow it down — {prompt}"

    reply = interrupt({"question": question, "stage": "discovery"})
    return {
        "turn": turn,
        "pending_answer": None,
        "transcript": [
            {"role": "assistant", "content": question},
            {"role": "user", "content": reply},
        ],
    }


async def auto_category_node(state: DiscoveryState) -> dict:
    """Only reached when a loan type has 0 or 1 category — nothing to ask."""
    lt = _lt_entry(state)
    categories = lt.get("categories", [])
    return {"category": categories[0]["code"] if categories else None}


async def present_node(state: DiscoveryState) -> dict:
    loan_type = state["loan_type"]
    category = state.get("category")
    turn = state.get("turn", 0) + 1
    preamble = ""

    bank_id = _bank_id(state)
    try:
        products = await core_banking.list_products(loan_type, category, bank_id=bank_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 404:
            raise
        preamble = (
            "We don't currently offer that specific option. "
            "Here's what we do have for this loan type instead:\n\n"
        )
        products = await core_banking.list_products(loan_type, bank_id=bank_id)

    # The product details themselves are NOT put in the chat text — they go
    # out as structured `products` (see api/interview.py -> TurnResponse)
    # so the frontend renders one card per product instead of a wall of
    # bulleted text. (An earlier version had the LLM freely "present the
    # products" in prose, which — with several in play — would quietly
    # summarise, merge, or drop some of them down to just one. Building the
    # per-product text deterministically fixed that, but a bullet list is
    # still a worse read than an actual card, hence this.)
    #
    # briefs travels inside the interrupt payload itself, not the node's
    # return dict — a node that calls interrupt() re-runs from the top on
    # resume, and only its (eventual) return value gets committed to
    # checkpointed state, so `state["products"]` would still be stale/empty
    # at the exact moment the frontend needs this turn's product list.
    briefs = [_product_brief(p) for p in products]
    lead_in = "Here's what's available:"
    ask = "Which would you like to proceed with?"
    question = f"{preamble}{lead_in}\n\n{ask}"

    reply = interrupt({"question": question, "stage": "product_selection", "products": briefs})

    return {
        "turn": turn,
        "products": products,
        "transcript": [
            {"role": "assistant", "content": question},
            {"role": "user", "content": reply},
        ],
    }


async def select_node(state: DiscoveryState) -> dict:
    reply = state["transcript"][-1]["content"]
    products = state.get("products") or []
    valid_codes = {p["product_code"] for p in products}

    llm = get_llm("interaction")
    resp = await llm.ainvoke([
        SystemMessage(content=SELECT_SYSTEM),
        HumanMessage(content=json.dumps({
            "products": [_product_brief(p) for p in products],
            "applicant_reply": reply,
        }, ensure_ascii=False)),
    ])
    parsed = _parse(as_text(resp))

    chosen = parsed.get("product_code")
    if chosen not in valid_codes:
        chosen = None

    return {
        "product_code": chosen,
        "pending_answer": parsed.get("reply_to_question"),
    }


async def done_node(state: DiscoveryState) -> dict:
    return {"pending_answer": None}


def route_after_classify_type(state: DiscoveryState) -> Literal["classify_category", "auto_category", "clarify_type"]:
    if not state.get("loan_type"):
        return "clarify_type"
    categories = _lt_entry(state).get("categories", [])
    return "classify_category" if len(categories) > 1 else "auto_category"


def route_after_classify_category(state: DiscoveryState) -> Literal["present", "clarify_category"]:
    return "present" if state.get("category") else "clarify_category"


def route_after_select(state: DiscoveryState) -> Literal["done", "present"]:
    return "done" if state.get("product_code") else "present"


def build_discovery_graph(checkpointer=None):
    g = StateGraph(DiscoveryState)
    g.add_node("greet", greet_node)
    g.add_node("classify_type", classify_type_node)
    g.add_node("clarify_type", clarify_type_node)
    g.add_node("classify_category", classify_category_node)
    g.add_node("clarify_category", clarify_category_node)
    g.add_node("auto_category", auto_category_node)
    g.add_node("present", present_node)
    g.add_node("select", select_node)
    g.add_node("done", done_node)

    g.add_edge(START, "greet")
    g.add_edge("greet", "classify_type")
    g.add_conditional_edges(
        "classify_type", route_after_classify_type,
        {"classify_category": "classify_category", "auto_category": "auto_category", "clarify_type": "clarify_type"},
    )
    g.add_edge("clarify_type", "classify_type")
    g.add_conditional_edges(
        "classify_category", route_after_classify_category,
        {"present": "present", "clarify_category": "clarify_category"},
    )
    g.add_edge("clarify_category", "classify_category")
    g.add_edge("auto_category", "present")
    g.add_edge("present", "select")
    g.add_conditional_edges(
        "select", route_after_select, {"done": "done", "present": "present"},
    )
    g.add_edge("done", END)

    return g.compile(checkpointer=checkpointer or MemorySaver())