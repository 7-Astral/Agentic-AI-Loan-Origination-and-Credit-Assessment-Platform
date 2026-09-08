import uuid

from fastapi.testclient import TestClient
from sqlalchemy import delete

from core.database import AsyncSessionLocal, engine
from main import app
from models.bank import Bank
from models.conversation import Conversation
from models.enums import BankStatus
from models.message import Message


async def _create_bank_and_conversation() -> tuple[uuid.UUID, uuid.UUID]:
    slug = f"request-details-test-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as db:
        bank = Bank(
            name="Request Details Test Bank",
            slug=slug,
            branding={"primary_color": "#444444", "logo_url": "/x.svg"},
            status=BankStatus.active,
        )
        db.add(bank)
        await db.flush()
        conversation = Conversation(bank_id=bank.id)
        db.add(conversation)
        await db.commit()
        return bank.id, conversation.id


async def _cleanup(bank_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Message).where(Message.conversation_id == conversation_id))
        await db.execute(delete(Conversation).where(Conversation.id == conversation_id))
        await db.execute(delete(Bank).where(Bank.id == bank_id))
        await db.commit()


async def test_request_details_with_specific_missing_fields_names_them() -> None:
    bank_id, conversation_id = await _create_bank_and_conversation()
    await engine.dispose()

    try:
        with TestClient(app) as client:
            response = client.post(
                f"/agents/conversations/{conversation_id}/request-details",
                json={
                    "five_c": "capacity",
                    "missing_fields": ["Income frequency", "Monthly expenses"],
                },
            )
            assert response.status_code == 201
            body = response.json()
            assert body["role"] == "assistant"
            assert "Capacity" in body["content"]
            assert "Income frequency" in body["content"]
            assert "Monthly expenses" in body["content"]

            state = client.get(f"/agents/conversations/{conversation_id}").json()
            assert any(m["content"] == body["content"] for m in state["messages"])
    finally:
        await _cleanup(bank_id, conversation_id)


async def test_request_details_without_missing_fields_uses_generic_ask() -> None:
    bank_id, conversation_id = await _create_bank_and_conversation()
    await engine.dispose()

    try:
        with TestClient(app) as client:
            response = client.post(
                f"/agents/conversations/{conversation_id}/request-details",
                json={"five_c": "collateral"},
            )
        assert response.status_code == 201
        body = response.json()
        assert "Collateral" in body["content"]
        assert "valuation" in body["content"].lower()
    finally:
        await _cleanup(bank_id, conversation_id)


async def test_request_details_404_for_unknown_conversation() -> None:
    with TestClient(app) as client:
        response = client.post(
            f"/agents/conversations/{uuid.uuid4()}/request-details",
            json={"five_c": "character"},
        )
    assert response.status_code == 404
