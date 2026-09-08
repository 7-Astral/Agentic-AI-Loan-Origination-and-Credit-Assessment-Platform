import uuid

from fastapi.testclient import TestClient
from sqlalchemy import delete

from core.database import AsyncSessionLocal, engine
from main import app
from models.bank import Bank
from models.conversation import Conversation
from models.enums import BankStatus, LoanType


async def test_list_conversations_includes_bank_name_and_totals() -> None:
    """This bank is deliberately NOT `is_test` (it exercises the real, visible path the
    frontend Applications list uses), so it must be cleaned up rather than left behind as
    permanent list pollution — unlike the other test-bank fixtures in this suite, which
    rely on `is_test=True` to stay hidden instead."""
    slug = f"list-test-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as db:
        bank = Bank(
            name="List Test Bank",
            slug=slug,
            branding={"primary_color": "#111111", "logo_url": "/x.svg"},
            status=BankStatus.active,
        )
        db.add(bank)
        await db.flush()
        conversation = Conversation(bank_id=bank.id, selected_loan_type=LoanType.personal)
        db.add(conversation)
        await db.commit()
        bank_id = bank.id
        conversation_id = conversation.id

    await engine.dispose()

    try:
        with TestClient(app) as client:
            response = client.get("/agents/conversations")

        assert response.status_code == 200
        rows = response.json()
        match = next(r for r in rows if r["id"] == str(conversation_id))
        assert match["bank_name"] == "List Test Bank"
        assert match["selected_loan_type"] == "personal"
        assert match["status"] == "active"
    finally:
        # TestClient drove the engine on its own portal-thread loop; dispose before
        # reopening a session here, or pooled connections bound to that closed loop
        # raise "Event loop is closed" (same gotcha documented in tests/conftest.py).
        await engine.dispose()
        async with AsyncSessionLocal() as db:
            await db.execute(delete(Conversation).where(Conversation.id == conversation_id))
            await db.execute(delete(Bank).where(Bank.id == bank_id))
            await db.commit()


async def test_list_conversations_excludes_test_bank_conversations() -> None:
    slug = f"hidden-test-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as db:
        bank = Bank(
            name="Hidden Test Bank",
            slug=slug,
            branding={"primary_color": "#222222", "logo_url": "/x.svg"},
            status=BankStatus.active,
            is_test=True,
        )
        db.add(bank)
        await db.flush()
        conversation = Conversation(bank_id=bank.id)
        db.add(conversation)
        await db.commit()
        conversation_id = conversation.id

    await engine.dispose()

    with TestClient(app) as client:
        response = client.get("/agents/conversations")

    assert response.status_code == 200
    ids = {row["id"] for row in response.json()}
    assert str(conversation_id) not in ids


async def test_delete_conversation_hides_it_without_removing_the_row() -> None:
    slug = f"delete-test-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as db:
        bank = Bank(
            name="Delete Test Bank",
            slug=slug,
            branding={"primary_color": "#333333", "logo_url": "/x.svg"},
            status=BankStatus.active,
        )
        db.add(bank)
        await db.flush()
        conversation = Conversation(bank_id=bank.id)
        db.add(conversation)
        await db.commit()
        bank_id = bank.id
        conversation_id = conversation.id

    await engine.dispose()

    try:
        with TestClient(app) as client:
            delete_response = client.delete(f"/agents/conversations/{conversation_id}")
            assert delete_response.status_code == 204

            list_response = client.get("/agents/conversations")
            ids = {row["id"] for row in list_response.json()}
            assert str(conversation_id) not in ids

        await engine.dispose()
        async with AsyncSessionLocal() as db:
            stored = await db.get(Conversation, conversation_id)
            assert stored is not None
            assert stored.hidden is True
    finally:
        await engine.dispose()
        async with AsyncSessionLocal() as db:
            await db.execute(delete(Conversation).where(Conversation.id == conversation_id))
            await db.execute(delete(Bank).where(Bank.id == bank_id))
            await db.commit()


async def test_delete_conversation_404_for_unknown_id() -> None:
    with TestClient(app) as client:
        response = client.delete(f"/agents/conversations/{uuid.uuid4()}")

    assert response.status_code == 404
