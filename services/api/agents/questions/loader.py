import uuid
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import LoanType
from models.question_template import QuestionTemplate
from schemas.question import Question


async def _get_template(
    db: AsyncSession, bank_id: uuid.UUID, loan_type: LoanType | None
) -> QuestionTemplate | None:
    """Returns the active question template for `loan_type` (None = baseline), preferring
    one scoped to `bank_id` over the platform default (bank_id IS NULL), latest version."""
    loan_type_filter = (
        QuestionTemplate.loan_type == loan_type
        if loan_type is not None
        else QuestionTemplate.loan_type.is_(None)
    )
    stmt = (
        select(QuestionTemplate)
        .where(
            QuestionTemplate.is_active.is_(True),
            loan_type_filter,
            or_(QuestionTemplate.bank_id == bank_id, QuestionTemplate.bank_id.is_(None)),
        )
        .order_by(QuestionTemplate.bank_id.is_(None), QuestionTemplate.version.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().first()


def parse_questions(raw: list[dict[str, Any]]) -> list[Question]:
    return [Question.model_validate(item) for item in raw]


async def get_question_set(
    db: AsyncSession, bank_id: uuid.UUID, loan_type: LoanType
) -> list[Question]:
    """Returns the ordered, merged question set for `loan_type`: the baseline set
    (loan_type IS NULL) followed by the type-specific set. Entirely database-driven —
    adding, reordering or removing a question requires no code change."""
    questions: list[Question] = []

    baseline = await _get_template(db, bank_id, None)
    if baseline is not None:
        questions.extend(parse_questions(baseline.questions))

    specific = await _get_template(db, bank_id, loan_type)
    if specific is not None:
        questions.extend(parse_questions(specific.questions))

    return questions
