import re
from decimal import Decimal, InvalidOperation
from typing import Any

from schemas.question import Question, QuestionType

_NUMBER_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(k|m)?", re.IGNORECASE)

_TRUE_PHRASES = [
    "yes",
    "yeah",
    "yep",
    "yup",
    "correct",
    "true",
    "i do",
    "i have",
    "sure",
    "affirmative",
]
_FALSE_PHRASES = [
    "no",
    "nope",
    "nah",
    "not really",
    "false",
    "i don't",
    "i do not",
    "negative",
    "none",
]


def parse_number(raw: str) -> Decimal | None:
    """Extracts a numeric value from free-form text, handling `$`, thousands separators,
    and `k`/`m` shorthand — e.g. "about 85k", "$85,000" and "85000 a year" all parse to 85000."""
    cleaned = raw.replace(",", "").replace("$", "")
    match = _NUMBER_RE.search(cleaned)
    if not match:
        return None
    try:
        value = Decimal(match.group(1))
    except InvalidOperation:
        return None
    suffix = (match.group(2) or "").lower()
    if suffix == "k":
        value *= 1000
    elif suffix == "m":
        value *= 1_000_000
    return value


def parse_boolean(raw: str) -> bool | None:
    text = raw.strip().lower()
    for phrase in sorted(_FALSE_PHRASES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(phrase)}\b", text):
            return False
    for phrase in sorted(_TRUE_PHRASES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(phrase)}\b", text):
            return True
    return None


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def match_choice(raw: str, options: list[str]) -> str | None:
    normalized_raw = _normalize(raw)
    if not normalized_raw:
        return None
    for option in options:
        if _normalize(option) == normalized_raw:
            return option
    for option in options:
        normalized_option = _normalize(option)
        if normalized_option in normalized_raw or normalized_raw in normalized_option:
            return option
    return None


def extract_value(question: Question, raw: str) -> Any | None:
    """Deterministic extraction of a typed value from free text. Returns None when the
    text can't be confidently parsed, signalling callers to fall back to LLM-assisted
    extraction (see `answer_resolver.py`)."""
    if question.type in (QuestionType.currency, QuestionType.number):
        return parse_number(raw)
    if question.type == QuestionType.integer:
        value = parse_number(raw)
        return int(value) if value is not None else None
    if question.type == QuestionType.boolean:
        return parse_boolean(raw)
    if question.type == QuestionType.choice:
        return match_choice(raw, question.options or [])
    if question.type == QuestionType.text:
        text = raw.strip()
        return text if text else None
    return None


def validate_value(question: Question, value: Any) -> bool:
    """Pure code-side acceptance check for an already-extracted value — the model may
    normalise phrasing, but code alone decides whether a value is acceptable."""
    if value is None:
        return False

    if question.type in (QuestionType.currency, QuestionType.number, QuestionType.integer):
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            return False
        if question.type == QuestionType.integer and not float(value).is_integer():
            return False
        if question.validation is not None:
            if question.validation.min is not None and value < question.validation.min:
                return False
            if question.validation.max is not None and value > question.validation.max:
                return False
        return True

    if question.type == QuestionType.boolean:
        return isinstance(value, bool)

    if question.type == QuestionType.choice:
        return isinstance(value, str) and value in (question.options or [])

    if question.type == QuestionType.text:
        return isinstance(value, str) and len(value.strip()) > 0

    return False
