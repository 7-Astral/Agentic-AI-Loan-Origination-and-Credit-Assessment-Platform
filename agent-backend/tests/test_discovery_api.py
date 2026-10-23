"""Discovery flow via the HTTP API — this is exactly where this project's
own bugs lived this session: products silently collapsing to one card, and
a stage-name mismatch that left the product-selection button disabled.
Drives POST /api/v1/applications and .../messages through greet -> classify
type -> (clarify or auto-category) -> present (product cards) -> select ->
handoff into the interview, with the LLM and catalog both stubbed."""
import json

import pytest

from tests.conftest import auth_headers


@pytest.fixture
def customer():
    """One fixed customer identity for the whole test — a chat session is
    owned by whoever started it, so every call in a test must reuse the
    same token or _check_ownership's 403 kicks in (see app.api.interview)."""
    return auth_headers()


async def _start(client, customer):
    return await client.post("/api/v1/applications", json={}, headers=customer)


async def _send(client, session_id, customer, message):
    return await client.post(
        f"/api/v1/applications/{session_id}/messages", json={"message": message}, headers=customer
    )


async def test_first_turn_is_a_discovery_question(client, fake_catalog, customer):
    resp = await _start(client, customer)
    assert resp.status_code == 200
    body = resp.json()
    assert body["stage"] == "discovery"
    assert body["complete"] is False
    assert body["products"] is None
    assert "loan" in body["question"].lower() or "help" in body["question"].lower()


async def test_product_selection_turn_carries_every_matching_product_as_cards(client, fake_catalog, fake_llm, customer):
    """The actual regression this session hit: a bank with TWO products
    under one loan type/category must show BOTH as cards, not just one."""
    session_id = (await _start(client, customer)).json()["session_id"]

    # classify_type_node's LLM call: pick "home".
    fake_llm.discovery_queue.append(json.dumps({"loan_type": "home", "confidence": "high", "reply_to_question": None}))
    # classify_category_node's LLM call: pick "owner_occupied".
    fake_llm.discovery_queue.append(json.dumps({"category": "owner_occupied", "confidence": "high", "reply_to_question": None}))

    resp = await _send(client, session_id, customer, "I want to buy a house to live in")
    assert resp.status_code == 200
    body = resp.json()
    assert body["stage"] == "product_selection"
    assert body["complete"] is False

    # This is the exact contract the frontend's product-card UI depends on.
    assert body["products"] is not None
    codes = {p["product_code"] for p in body["products"]}
    assert codes == {"HOME-BBBB2222", "HOME-CCCC3333"}
    names = {p["name"] for p in body["products"]}
    assert names == {"Home Purchase Loan", "Home Renovation Loan"}


async def test_low_confidence_classification_asks_a_clarifying_question_instead_of_guessing(client, fake_catalog, fake_llm, customer):
    session_id = (await _start(client, customer)).json()["session_id"]

    fake_llm.discovery_queue.append(json.dumps({"loan_type": None, "confidence": "low", "reply_to_question": None}))

    resp = await _send(client, session_id, customer, "not sure yet")
    body = resp.json()
    assert body["stage"] == "discovery"
    assert body["products"] is None
    assert "personal loan" in body["question"].lower() or "home loan" in body["question"].lower()


async def test_single_category_loan_type_skips_the_category_question(client, fake_catalog, fake_llm, customer):
    """"personal" has exactly one category in the fixture catalog — the
    graph must go straight to auto_category, never asking a redundant
    "which category" question when there's only one possible answer."""
    session_id = (await _start(client, customer)).json()["session_id"]

    fake_llm.discovery_queue.append(json.dumps({"loan_type": "personal", "confidence": "high", "reply_to_question": None}))

    resp = await _send(client, session_id, customer, "I need a personal loan")
    body = resp.json()
    assert body["stage"] == "product_selection"
    codes = {p["product_code"] for p in body["products"]}
    assert codes == {"PERSONAL-AAAA1111"}


async def test_selecting_a_product_hands_off_into_the_interview(client, fake_catalog, fake_llm, customer):
    session_id = (await _start(client, customer)).json()["session_id"]

    fake_llm.discovery_queue.append(json.dumps({"loan_type": "personal", "confidence": "high", "reply_to_question": None}))
    resp = await _send(client, session_id, customer, "personal loan please")
    assert resp.json()["stage"] == "product_selection"

    # select_node's LLM call: match the reply to the one product on offer.
    fake_llm.discovery_queue.append(json.dumps({"product_code": "PERSONAL-AAAA1111", "reply_to_question": None}))
    # First slot's ask_node question (interview graph has taken over) — this
    # is a fresh (non-resumed) ask_node call, content-routed by FakeLLM, not
    # part of the discovery queue.
    fake_llm.ask_texts["loan_amount"] = "How much would you like to borrow?"

    resp = await _send(client, session_id, customer, "the quick personal loan")
    body = resp.json()
    assert body["stage"] == "interview"
    assert body["product_code"] == "PERSONAL-AAAA1111"
    assert body["question"] == "How much would you like to borrow?"


async def test_unmatched_selection_reply_reshows_the_cards(client, fake_catalog, fake_llm, customer):
    session_id = (await _start(client, customer)).json()["session_id"]
    fake_llm.discovery_queue.append(json.dumps({"loan_type": "personal", "confidence": "high", "reply_to_question": None}))
    await _send(client, session_id, customer, "personal")

    fake_llm.discovery_queue.append(json.dumps({"product_code": None, "reply_to_question": "Which one did you mean?"}))
    resp = await _send(client, session_id, customer, "the good one")
    body = resp.json()
    assert body["stage"] == "product_selection"
    assert body["products"] is not None


async def test_explicit_product_code_skips_discovery_entirely(client, fake_catalog, fake_llm, customer):
    fake_llm.ask_texts["loan_amount"] = "How much would you like to borrow?"
    resp = await client.post(
        "/api/v1/applications", json={"product_code": "PERSONAL-AAAA1111"}, headers=customer
    )
    body = resp.json()
    assert resp.status_code == 200
    assert body["stage"] == "interview"
    assert body["product_code"] == "PERSONAL-AAAA1111"


async def test_unauthenticated_session_start_is_allowed_anonymous(client, fake_catalog):
    """No Authorization header still starts a session — get_customer_id_from_token
    returns None rather than rejecting, matching the terminal test scripts'
    existing anonymous usage (see app.core.identity's own docstring)."""
    resp = await client.post("/api/v1/applications", json={})
    assert resp.status_code == 200


async def test_a_different_customers_token_cannot_continue_someone_elses_session(client, fake_catalog, customer):
    session_id = (await _start(client, customer)).json()["session_id"]
    resp = await _send(client, session_id, auth_headers(), "hello")
    assert resp.status_code == 403


async def test_unknown_session_id_is_404(client, fake_catalog, customer):
    resp = await _send(client, "00000000-0000-0000-0000-000000000000", customer, "hello")
    assert resp.status_code == 404
