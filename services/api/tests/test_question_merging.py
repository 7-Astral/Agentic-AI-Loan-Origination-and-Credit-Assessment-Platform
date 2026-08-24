import uuid

import pytest

from agents.questions.loader import get_question_set
from core.database import AsyncSessionLocal
from models.enums import LoanType
from scripts.seed import (
    BASELINE_QUESTIONS,
    BUSINESS_QUESTIONS,
    CAR_QUESTIONS,
    HOME_QUESTIONS,
    INVESTMENT_QUESTIONS,
    PERSONAL_QUESTIONS,
    seed,
)

BASELINE_KEYS = [q["key"] for q in BASELINE_QUESTIONS]

EXPECTED_KEYS = {
    LoanType.home: BASELINE_KEYS + [q["key"] for q in HOME_QUESTIONS],
    LoanType.investment: BASELINE_KEYS + [q["key"] for q in INVESTMENT_QUESTIONS],
    LoanType.personal: BASELINE_KEYS + [q["key"] for q in PERSONAL_QUESTIONS],
    LoanType.car: BASELINE_KEYS + [q["key"] for q in CAR_QUESTIONS],
    LoanType.business: BASELINE_KEYS + [q["key"] for q in BUSINESS_QUESTIONS],
}


@pytest.mark.parametrize("loan_type", list(EXPECTED_KEYS))
async def test_merged_question_order(loan_type: LoanType) -> None:
    await seed()
    async with AsyncSessionLocal() as db:
        questions = await get_question_set(db, uuid.uuid4(), loan_type)
    assert [q.key for q in questions] == EXPECTED_KEYS[loan_type]
