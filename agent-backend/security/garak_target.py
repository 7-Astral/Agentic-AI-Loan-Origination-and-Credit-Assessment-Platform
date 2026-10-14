import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from app.core.sync_runner import run

PRODUCT = {
    "name": "Everyday Personal Loan",
    "interest_rate": 9.49,
    "min_amount": 5000,
    "max_amount": 50000,
    "max_term_months": 84,
}
SLOTS = [
    {"id": "full_name", "label": "Full name"},
    {"id": "loan_amount", "label": "Loan amount"},
    {"id": "gross_income", "label": "Gross income"},
]
FILLED = {"full_name": "Sam Taylor", "loan_amount": 20000, "gross_income": 85000}


async def _advisor(prompt: str, guarded: bool) -> str:
    from app.agents.interaction.advisor import answer_question
    from app.core.injection_guard import BLOCKED_MESSAGE, InjectionBlocked, screen

    if guarded:
        try:
            await screen(prompt, "garak")
        except InjectionBlocked:
            return BLOCKED_MESSAGE
    return await answer_question(prompt, PRODUCT, SLOTS, FILLED, [])


def advisor(prompt: str, **kwargs) -> list[str]:
    return [run(_advisor(prompt, guarded=True))]


def advisor_unguarded(prompt: str, **kwargs) -> list[str]:
    return [run(_advisor(prompt, guarded=False))]
