"""The slot-filling interview graph end to end via the HTTP API: ask ->
extract -> validate -> next batch, repeated until every required slot is
filled, then GET the assembled application and POST /submit to hand it
into the main platform's real loan pipeline (services/api), with the
catalog client stubbed via fake_catalog.submit_application.

Fixture schema (see tests/conftest.py DEFAULT_SLOTS): loan_amount
(currency, phase 1), loan_term_months (number, phase 1), loan_purpose
(choice, phase 2) — each its own group, so with the default batch size of
one, filling the interview takes exactly three turns.

fake_llm.ask_texts / .extract_responses are keyed by slot id rather than
called in a strict order — see the FakeLLM docstring in conftest.py for
why: ask_node calls the LLM again (and discards the result) every time its
own interrupt() is resumed, so a fixed call-order queue can't express this
without hardcoding that quirk into every test."""
import pytest

from tests.conftest import auth_headers


@pytest.fixture
def customer():
    return auth_headers()


def _configure(fake_llm):
    fake_llm.ask_texts.update(
        {
            "loan_amount": "How much would you like to borrow?",
            "loan_term_months": "Over how many months?",
            "loan_purpose": "What's this loan for?",
        }
    )


async def _start_interview(client, customer, fake_llm, product_code="PERSONAL-AAAA1111"):
    _configure(fake_llm)
    return await client.post("/api/v1/applications", json={"product_code": product_code}, headers=customer)


async def _send(client, session_id, customer, message):
    return await client.post(
        f"/api/v1/applications/{session_id}/messages", json={"message": message}, headers=customer
    )


async def _fill_everything(client, session_id, customer, fake_llm):
    """Drives the three remaining turns (amount, term, purpose) to
    completion. Assumes the interview's opening question has already been
    consumed by _start_interview."""
    fake_llm.extract_responses["loan_amount"] = {"values": {"loan_amount": 25000}, "unclear": [], "notes": ""}
    await _send(client, session_id, customer, "$25,000")

    fake_llm.extract_responses["loan_term_months"] = {"values": {"loan_term_months": 36}, "unclear": [], "notes": ""}
    await _send(client, session_id, customer, "36 months")

    fake_llm.extract_responses["loan_purpose"] = {"values": {"loan_purpose": "car"}, "unclear": [], "notes": ""}
    return await _send(client, session_id, customer, "buying a car")


async def test_full_interview_fills_every_slot_then_completes(client, fake_catalog, fake_llm, customer):
    start = await _start_interview(client, customer, fake_llm)
    body = start.json()
    assert body["stage"] == "interview"
    assert body["complete"] is False
    assert body["progress"]["answered"] == 0
    session_id = body["session_id"]

    resp = await _fill_everything(client, session_id, customer, fake_llm)
    body = resp.json()
    assert body["stage"] == "complete"
    assert body["complete"] is True
    assert body["progress"]["complete"] is True


async def test_ask_llm_called_exactly_once_per_slot_not_twice(client, fake_catalog, fake_llm, customer):
    """Regression test for a real bug found while building this suite:
    ask_node used to call the questioner LLM *before* interrupt() inside the
    same node, and because a LangGraph node that calls interrupt() re-runs
    from the top on every resume, that call fired twice per slot — once
    shown to the applicant, once discarded (but written to the transcript
    instead). Fixed by splitting the question computation into its own
    non-interrupting node (compose_question_node in app/agents/interaction/
    graph.py) so it only ever runs once per slot. Each of the 3 default
    slots (see conftest.py DEFAULT_SLOTS) should produce exactly one
    questioner call across the whole interview, not six."""
    start = await _start_interview(client, customer, fake_llm)
    session_id = start.json()["session_id"]
    await _fill_everything(client, session_id, customer, fake_llm)

    ask_calls = [c for c in fake_llm.calls if "You are a loan application assistant" in c[0].content]
    assert len(ask_calls) == 3, (
        f"expected exactly one questioner call per slot (3 slots), got {len(ask_calls)} — "
        "ask_node may be recomputing the question again on resume"
    )


async def test_intermediate_turn_reports_progress_and_next_question(client, fake_catalog, fake_llm, customer):
    start = await _start_interview(client, customer, fake_llm)
    session_id = start.json()["session_id"]

    fake_llm.extract_responses["loan_amount"] = {"values": {"loan_amount": 25000}, "unclear": [], "notes": ""}
    resp = await _send(client, session_id, customer, "About $25,000")
    body = resp.json()
    assert body["stage"] == "interview"
    assert body["progress"]["answered"] == 1
    assert body["question"] == "Over how many months?"


async def test_unrecognized_reply_reasks_without_advancing(client, fake_catalog, fake_llm, customer):
    """extractor returns nothing usable -> repair -> the same slot gets
    asked again, progress doesn't move on."""
    start = await _start_interview(client, customer, fake_llm)
    session_id = start.json()["session_id"]

    # No extract_responses entry for loan_amount -> FakeLLM's default is an
    # empty extraction, exactly like a real "I couldn't parse anything usable".
    resp = await _send(client, session_id, customer, "what's your interest rate?")
    body = resp.json()
    assert body["stage"] == "interview"
    assert body["progress"]["answered"] == 0
    # Still the loan_amount question (re-asked, repair mode) — batching
    # never advanced to loan_term_months.
    assert body["question"] == "How much would you like to borrow?"


async def test_a_value_failing_validation_does_not_get_committed(client, fake_catalog, fake_llm, customer):
    """loan_amount's validation caps it at 1,000,000 — an out-of-range
    extracted value must be rejected, not silently stored."""
    start = await _start_interview(client, customer, fake_llm)
    session_id = start.json()["session_id"]

    fake_llm.extract_responses["loan_amount"] = {"values": {"loan_amount": 5_000_000}, "unclear": [], "notes": ""}
    resp = await _send(client, session_id, customer, "5 million")
    body = resp.json()
    assert body["stage"] == "interview"
    assert body["progress"]["answered"] == 0


async def test_get_application_reflects_filled_slots(client, fake_catalog, fake_llm, customer):
    start = await _start_interview(client, customer, fake_llm)
    session_id = start.json()["session_id"]

    fake_llm.extract_responses["loan_amount"] = {"values": {"loan_amount": 15000}, "unclear": [], "notes": ""}
    await _send(client, session_id, customer, "$15,000")

    resp = await client.get(f"/api/v1/applications/{session_id}", headers=customer)
    assert resp.status_code == 200
    body = resp.json()
    assert body["filled"]["loan_amount"] == 15000.0
    assert body["provenance"]["loan_amount"]["source"] == "extracted"


async def test_get_application_during_discovery_is_409(client, fake_catalog, customer):
    resp = await client.post("/api/v1/applications", json={}, headers=customer)
    session_id = resp.json()["session_id"]

    resp = await client.get(f"/api/v1/applications/{session_id}", headers=customer)
    assert resp.status_code == 409


async def test_submit_requires_interview_complete(client, fake_catalog, fake_llm, customer):
    start = await _start_interview(client, customer, fake_llm)
    session_id = start.json()["session_id"]

    resp = await client.post(f"/api/v1/applications/{session_id}/submit", headers=customer)
    assert resp.status_code == 409


async def test_submit_hands_the_completed_interview_to_the_real_pipeline(client, fake_catalog, fake_llm, customer):
    start = await _start_interview(client, customer, fake_llm)
    session_id = start.json()["session_id"]

    resp = await _fill_everything(client, session_id, customer, fake_llm)
    assert resp.json()["stage"] == "complete"

    resp = await client.post(f"/api/v1/applications/{session_id}/submit", headers=customer)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["outcome"] == "auto_approved"

    # The fake catalog recorded exactly what submit_application sent through.
    assert len(fake_catalog.submitted_applications) == 1
    submitted = fake_catalog.submitted_applications[0]
    assert submitted["product_code"] == "PERSONAL-AAAA1111"
    assert submitted["requested_amount"] == 25000.0
    assert submitted["tenure_requested_months"] == 36
    assert submitted["external_reference"] == session_id


async def test_submit_without_a_customer_token_is_rejected(client, fake_catalog, fake_llm):
    """submit_application requires a resolvable applicant_id — an anonymous
    session with no customer ever attached has nothing to submit as."""
    _configure(fake_llm)
    start = await client.post("/api/v1/applications", json={"product_code": "PERSONAL-AAAA1111"})
    session_id = start.json()["session_id"]

    await _fill_everything(client, session_id, {}, fake_llm)

    resp = await client.post(f"/api/v1/applications/{session_id}/submit")
    assert resp.status_code == 401
