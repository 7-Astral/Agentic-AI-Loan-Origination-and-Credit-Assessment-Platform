from typing import Any

from schemas.question import Question


def is_applicable(question: Question, collected_data: dict[str, Any]) -> bool:
    """A question with no `depends_on` is always applicable. Otherwise it's applicable
    only when the referenced answer has already been collected and matches `equals`."""
    if question.depends_on is None:
        return True
    return bool(collected_data.get(question.depends_on.key) == question.depends_on.equals)


def resolve_index(questions: list[Question], collected_data: dict[str, Any], index: int) -> int:
    """Advances `index` past any questions whose `depends_on` precondition isn't met,
    starting from `index`. Returns `len(questions)` once every remaining question is
    either answered or skipped."""
    while index < len(questions) and not is_applicable(questions[index], collected_data):
        index += 1
    return index
