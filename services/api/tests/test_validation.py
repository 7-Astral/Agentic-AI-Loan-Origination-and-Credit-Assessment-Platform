from decimal import Decimal

from agents.questions.validation import (
    extract_value,
    match_choice,
    parse_boolean,
    parse_number,
    validate_value,
)
from schemas.question import Question, QuestionValidation


def test_parse_number_handles_common_phrasings() -> None:
    assert parse_number("about 85k") == Decimal("85000")
    assert parse_number("$85,000") == Decimal("85000")
    assert parse_number("85000 a year") == Decimal("85000")


def test_parse_number_returns_none_when_no_digits() -> None:
    assert parse_number("not a number") is None


def test_parse_boolean_recognises_common_phrasings() -> None:
    assert parse_boolean("yes") is True
    assert parse_boolean("yeah") is True
    assert parse_boolean("I do") is True
    assert parse_boolean("no") is False
    assert parse_boolean("nope") is False
    assert parse_boolean("not really") is False
    assert parse_boolean("purple elephant") is None


def test_match_choice_exact_and_fuzzy() -> None:
    options = ["Full-time", "Part-time", "Casual"]
    assert match_choice("Full-time", options) == "Full-time"
    assert match_choice("full time", options) == "Full-time"
    assert match_choice("something else entirely", options) is None


def _currency_question(**overrides: object) -> Question:
    defaults: dict[str, object] = {
        "key": "annual_income",
        "prompt": "?",
        "type": "currency",
        "validation": QuestionValidation(min=0, max=10000000),
    }
    defaults.update(overrides)
    return Question.model_validate(defaults)


def test_validate_value_rejects_out_of_bounds() -> None:
    question = _currency_question()
    assert validate_value(question, Decimal("85000")) is True
    assert validate_value(question, Decimal("-5")) is False
    assert validate_value(question, Decimal("20000000")) is False


def test_validate_value_rejects_choice_outside_options() -> None:
    question = Question.model_validate(
        {
            "key": "employment_status",
            "prompt": "?",
            "type": "choice",
            "options": ["Full-time", "Part-time"],
        }
    )
    assert validate_value(question, "Full-time") is True
    assert validate_value(question, "Retired") is False


def test_extract_value_end_to_end_for_currency() -> None:
    question = _currency_question()
    value = extract_value(question, "about 85k")
    assert value == Decimal("85000")
    assert validate_value(question, value) is True
