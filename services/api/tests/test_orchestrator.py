import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from agents.clients.base import ChatMessage
from agents.orchestrator import handle_customer_message, start_conversation
from core.database import AsyncSessionLocal
from models.bank import Bank
from models.conversation import Conversation
from models.enums import BankStatus, LoanType
from models.loan_product import LoanProduct
from scripts.seed import seed


class FakeLLM:
    """Never calls a real API. `complete` returns a canned reply; `extract` returns queued
    canned JSON responses (used for Stage 1 loan-type identification, and as the fallback
    only when deterministic answer parsing fails)."""

    def __init__(self, extract_queue: list[str] | None = None) -> None:
        self._extract_queue = list(extract_queue or [])

    async def complete(self, system_prompt: str, messages: list[ChatMessage]) -> str:
        return "(agent reply)"

    async def extract(self, instruction: str, text: str) -> str:
        if self._extract_queue:
            return self._extract_queue.pop(0)
        return '{"value": null}'


async def _create_bank_with_home_product() -> Bank:
    async with AsyncSessionLocal() as db:
        bank = Bank(
            name="Orchestrator Test Bank",
            slug=f"orch-{uuid.uuid4().hex[:8]}",
            branding={"primary_color": "#000000", "logo_url": "/x.svg"},
            status=BankStatus.active,
        )
        db.add(bank)
        await db.flush()
        db.add(
            LoanProduct(
                bank_id=bank.id,
                name="Test Home Loan",
                type=LoanType.home,
                interest_rate=Decimal("6.00"),
                min_amount=Decimal("1000"),
                max_amount=Decimal("500000"),
                min_term_months=12,
                max_term_months=360,
                eligibility_rules={},
                active=True,
            )
        )
        await db.commit()
        await db.refresh(bank)
        return bank


async def test_valid_answer_advances_index_invalid_answer_does_not() -> None:
    await seed()
    bank = await _create_bank_with_home_product()

    async with AsyncSessionLocal() as db:
        conversation = Conversation(bank_id=bank.id)
        db.add(conversation)
        await db.flush()
        conversation_id = conversation.id
        await start_conversation(db, conversation, bank, llm=FakeLLM())
        await db.commit()

    async with AsyncSessionLocal() as db:
        conversation = await _get(db, conversation_id)
        await handle_customer_message(
            db,
            conversation,
            bank,
            "I want to buy a home",
            llm=FakeLLM(extract_queue=['{"loan_type": "home"}']),
        )
        await db.commit()
        assert conversation.selected_loan_type == LoanType.home
        first_index = conversation.current_question_index

    async with AsyncSessionLocal() as db:
        conversation = await _get(db, conversation_id)
        await handle_customer_message(db, conversation, bank, "asdkfjasldkfj??", llm=FakeLLM())
        await db.commit()
        assert conversation.current_question_index == first_index

    async with AsyncSessionLocal() as db:
        conversation = await _get(db, conversation_id)
        await handle_customer_message(db, conversation, bank, "Full-time", llm=FakeLLM())
        await db.commit()
        assert conversation.current_question_index == first_index + 1
        assert conversation.collected_data["employment_status"] == "Full-time"


async def _get(db: AsyncSession, conversation_id: uuid.UUID) -> Conversation:
    conversation = await db.get(Conversation, conversation_id)
    assert conversation is not None
    return conversation
