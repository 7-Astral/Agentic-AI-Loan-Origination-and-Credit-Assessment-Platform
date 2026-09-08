import uuid

import pytest

from agents.prompts.loader import get_system_prompt_content
from core.database import AsyncSessionLocal
from models.enums import LoanType
from scripts.seed import (
    BUSINESS_PROMPT_FOCUS,
    CAR_PROMPT_FOCUS,
    HOME_PROMPT_FOCUS,
    INVESTMENT_PROMPT_FOCUS,
    PERSONAL_PROMPT_FOCUS,
    seed,
)

EXPECTED_FOCUS = {
    LoanType.home: HOME_PROMPT_FOCUS,
    LoanType.investment: INVESTMENT_PROMPT_FOCUS,
    LoanType.personal: PERSONAL_PROMPT_FOCUS,
    LoanType.car: CAR_PROMPT_FOCUS,
    LoanType.business: BUSINESS_PROMPT_FOCUS,
}


async def test_baseline_prompt_has_no_loan_type_focus() -> None:
    await seed()
    async with AsyncSessionLocal() as db:
        content = await get_system_prompt_content(db, uuid.uuid4(), None)
    assert content is not None
    assert "LOAN FOCUS" not in content


@pytest.mark.parametrize("loan_type", list(EXPECTED_FOCUS))
async def test_loan_type_prompt_merges_baseline_and_focus(loan_type: LoanType) -> None:
    await seed()
    async with AsyncSessionLocal() as db:
        baseline = await get_system_prompt_content(db, uuid.uuid4(), None)
        content = await get_system_prompt_content(db, uuid.uuid4(), loan_type)

    assert baseline is not None and content is not None
    assert content.startswith(baseline)
    assert EXPECTED_FOCUS[loan_type] in content
