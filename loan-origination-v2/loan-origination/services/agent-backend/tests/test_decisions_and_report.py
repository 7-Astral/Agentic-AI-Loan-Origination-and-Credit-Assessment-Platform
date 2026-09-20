"""Staff-facing decision recording (app.api.decisions) and the
server-to-server chat report proxy (app.api.report) that services/api's
GET /bank/loan-applications/{id}/chat-report calls into. Both work off the
operational read-model directly — no LLM, no catalog — so applications are
seeded straight through app.services.operational rather than a full chat
flow."""
import uuid

import pytest_asyncio

from app.core.config import get_settings
from app.services.operational import ensure_application, mirror_transcript, mirror_turn


def _api_key_headers() -> dict[str, str]:
    return {"X-API-Key": get_settings().catalog_api_key}


@pytest_asyncio.fixture
async def application(db):
    session_id = str(uuid.uuid4())
    await ensure_application(session_id, bank_id="bank-1", status="documents")
    return session_id


# ------------------------------------------------------------- decisions --

async def test_post_decision_updates_application_status(client, application):
    resp = await client.post(
        f"/api/v1/applications/{application}/decision",
        json={"outcome": "approved", "reasoning": "Meets policy"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["outcome"] == "approved"
    assert body["reasoning"] == "Meets policy"


async def test_post_decision_refer_to_underwriter_maps_to_underwriter_review_status(client, application):
    resp = await client.post(
        f"/api/v1/applications/{application}/decision",
        json={"outcome": "refer_to_underwriter", "reasoning": "Needs a human look"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "underwriter_review"


async def test_post_decision_unknown_session_is_404(client):
    resp = await client.post(
        "/api/v1/applications/00000000-0000-0000-0000-000000000000/decision",
        json={"outcome": "approved"},
    )
    assert resp.status_code == 404


async def test_post_decision_rejects_invalid_outcome(client, application):
    resp = await client.post(
        f"/api/v1/applications/{application}/decision",
        json={"outcome": "maybe_later"},
    )
    assert resp.status_code == 422


# ------------------------------------------------------------------ report --

async def test_report_requires_service_api_key(client, application):
    resp = await client.get(f"/api/v1/applications/{application}/report")
    assert resp.status_code == 401

    resp = await client.get(f"/api/v1/applications/{application}/report", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


async def test_report_unknown_session_is_404(client):
    resp = await client.get(
        "/api/v1/applications/00000000-0000-0000-0000-000000000000/report", headers=_api_key_headers()
    )
    assert resp.status_code == 404


async def test_report_assembles_transcript_slots_and_decision(client, application):
    await mirror_transcript(
        application,
        [
            {"role": "assistant", "content": "How much would you like to borrow?"},
            {"role": "user", "content": "$25,000"},
        ],
        turn=1,
    )
    await mirror_turn(
        application,
        {
            "filled": {"loan_amount": 25000},
            "provenance": {"loan_amount": {"source": "extracted", "turn": 1}},
        },
        complete=False,
    )
    await client.post(f"/api/v1/applications/{application}/decision", json={"outcome": "approved", "reasoning": "ok"})

    resp = await client.get(f"/api/v1/applications/{application}/report", headers=_api_key_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == application
    assert len(body["transcript"]) == 2
    assert body["slots"] == [{"slot_key": "loan_amount", "value": 25000, "source": "extracted", "turn": 1}]
    assert body["decision"]["outcome"] == "approved"
    assert body["assessment"] is None
    assert body["documents"] == []
