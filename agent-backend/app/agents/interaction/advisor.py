import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import as_text, get_llm

SYSTEM = """You are a bank's loan assistant. The customer has finished the application
interview for the loan product described below and has not submitted it yet. They have
sent a message that is a question, a request for guidance, or a comment.

Rules:
- Answer from the product facts and the customer's own application details you are
  given. If the answer is not in them, say the bank's team can confirm it. Never invent
  rates, fees, limits or dates.
- You may explain how the product works, what a term means, and general things worth
  weighing up, such as how a longer term lowers each repayment but costs more interest
  overall. Present this as general information, not a personal recommendation.
- Never predict, hint at or promise the outcome. A member of the bank's staff reviews
  and decides every application.
- You cannot change the application yourself in this reply. If the customer seems to
  want an answer changed, ask them to say which detail and what the new value is.
- If the message is unrelated to their loan or application, say briefly that you can
  help with questions about this loan and their application.
- Reply in plain, friendly language, two to five sentences, no headings."""

FALLBACK = (
    "I can't answer that right now. You can ask me about this loan or your application, "
    "or tell me which detail you'd like to change and the new value."
)


async def answer_question(
    message: str,
    product: dict | None,
    slots: list[dict],
    filled: dict[str, Any],
    transcript: list[dict],
) -> str:
    labels = {s["id"]: s["label"] for s in slots}
    payload = {
        "product": product or {},
        "application_details": {labels.get(k, k): v for k, v in filled.items()},
        "recent_conversation": transcript[-6:],
        "customer_message": message,
    }
    try:
        llm = get_llm("interaction")
        resp = await llm.ainvoke(
            [SystemMessage(content=SYSTEM), HumanMessage(content=json.dumps(payload, ensure_ascii=False, default=str))]
        )
        return as_text(resp).strip() or FALLBACK
    except Exception:
        return FALLBACK
