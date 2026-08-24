import json
from decimal import Decimal, InvalidOperation
from typing import Any

from agents.clients.base import LLMProvider
from agents.questions.validation import extract_value, validate_value
from schemas.question import Question, QuestionType


def _build_extraction_instruction(question: Question) -> str:
    base = (
        "You extract a single structured answer value from a customer's chat message. "
        f'Reply with strict JSON only, in the form {{"value": <extracted value>}}. '
        'If the message does not answer the question at all, reply {"value": null}. '
        "Do not add any other text.\n\n"
        f"Question: {question.prompt}\n"
    )
    if question.type in (QuestionType.currency, QuestionType.number):
        return base + "Expected value type: a plain number (no currency symbols, no commas)."
    if question.type == QuestionType.integer:
        return base + "Expected value type: a whole number."
    if question.type == QuestionType.boolean:
        return base + "Expected value type: true or false."
    if question.type == QuestionType.choice:
        options = ", ".join(question.options or [])
        return base + f"Expected value: exactly one of these options: {options}."
    return base + "Expected value type: short text."


def _coerce(question: Question, value: Any) -> Any | None:
    if value is None:
        return None
    if question.type in (QuestionType.currency, QuestionType.number, QuestionType.integer):
        try:
            decimal_value = Decimal(str(value))
        except InvalidOperation:
            return None
        return int(decimal_value) if question.type == QuestionType.integer else decimal_value
    if question.type == QuestionType.boolean:
        if isinstance(value, bool):
            return value
        return None
    if question.type == QuestionType.choice:
        if isinstance(value, str) and question.options and value in question.options:
            return value
        return None
    if question.type == QuestionType.text:
        return str(value) if value else None
    return None


async def _extract_with_llm(question: Question, raw_text: str, llm: LLMProvider) -> Any | None:
    instruction = _build_extraction_instruction(question)
    try:
        raw = await llm.extract(instruction, raw_text)
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return _coerce(question, data.get("value"))


async def resolve_answer(question: Question, raw_text: str, llm: LLMProvider) -> tuple[bool, Any]:
    """Resolves the customer's free-text reply into a validated value for `question`.
    Tries a fast deterministic parse first; falls back to LLM-assisted extraction for
    phrasing it can't confidently handle. Code always makes the final accept/reject call —
    the model only ever normalises phrasing. Returns (accepted, value)."""
    value = extract_value(question, raw_text)
    if value is not None and validate_value(question, value):
        return True, value

    llm_value = await _extract_with_llm(question, raw_text, llm)
    if llm_value is not None and validate_value(question, llm_value):
        return True, llm_value

    return False, None
