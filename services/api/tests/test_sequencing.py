from agents.questions.loader import parse_questions
from agents.questions.sequencing import resolve_index
from scripts.seed import BASELINE_QUESTIONS

QUESTIONS = parse_questions(BASELINE_QUESTIONS)
DEBT_AMOUNT_INDEX = next(i for i, q in enumerate(QUESTIONS) if q.key == "existing_debt_amount")


def test_existing_debt_amount_skipped_when_existing_debts_false() -> None:
    index = resolve_index(QUESTIONS, {"existing_debts": False}, DEBT_AMOUNT_INDEX)
    assert QUESTIONS[index].key == "dependents"


def test_existing_debt_amount_asked_when_existing_debts_true() -> None:
    index = resolve_index(QUESTIONS, {"existing_debts": True}, DEBT_AMOUNT_INDEX)
    assert QUESTIONS[index].key == "existing_debt_amount"


def test_resolve_index_stops_at_end_of_list() -> None:
    index = resolve_index(QUESTIONS, {}, len(QUESTIONS))
    assert index == len(QUESTIONS)


def test_resolve_index_does_not_skip_questions_without_dependency() -> None:
    index = resolve_index(QUESTIONS, {}, 0)
    assert index == 0
