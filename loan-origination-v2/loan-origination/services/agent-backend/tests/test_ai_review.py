"""app.agents.assessment.ai_review — the one LLM step in the Five C's pipeline.

These are self-contained unit tests against `review()` directly: it takes plain
dicts/lists and calls `get_llm("assessment")`, so it needs neither the DB nor the
core_banking fakes `run_retail_assessment` itself needs — a lightweight fake LLM
object patched in per test is enough. `review()` must never raise; every case here
checks it degrades to `available: False` instead.
"""

import json

import pytest
from google.genai.errors import ServerError

from app.agents.assessment import ai_review

FINDINGS = dict(
    product_code="PERSONAL-AAAA1111",
    loan_amount=25000.0,
    loan_term_months=36,
    metrics={
        "gross_annual_income": {"state": "computed", "value": 85000.0, "unit": "AUD/year"},
        "credit_score": {"state": "computed", "value": 610, "unit": None},
    },
    rule_results=[{"rule_id": "dti_ceiling", "status": "flag", "message": "DTI above target"}],
    route_result={"tier": "underwriter_review", "fail_count": 0, "flag_count": 1, "provisional_count": 0},
)


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeLLM:
    """Returns each entry in `responses` in order; a `ServerError` entry is raised
    instead of returned, so a test can script "fails twice, then succeeds"."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls: list[list] = []

    async def ainvoke(self, messages):
        self.calls.append(messages)
        if not self.responses:
            raise AssertionError("no more scripted responses")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return _FakeMessage(item)


GOOD_RESPONSE = json.dumps({
    "risk_score": 42,
    "risk_band": "medium",
    "recommendation": "underwriter_review",
    "key_risk_factors": ["DTI above target"],
    "key_strengths": ["Stable declared income"],
    "rationale": "Income supports the loan but the flagged DTI rule warrants review.",
})


async def test_a_good_response_is_parsed_and_passed_through(monkeypatch):
    llm = _FakeLLM(GOOD_RESPONSE)
    monkeypatch.setattr(ai_review, "get_llm", lambda agent: llm)

    result = await ai_review.review(**FINDINGS)

    assert result["available"] is True
    assert result["risk_score"] == 42
    assert result["risk_band"] == "medium"
    assert result["recommendation"] == "underwriter_review"
    assert result["key_risk_factors"] == ["DTI above target"]
    assert result["key_strengths"] == ["Stable declared income"]
    assert "DTI" in result["rationale"]
    assert result["error"] is None

    # the model saw the deterministic findings, not raw declared/document data
    sent = json.loads(llm.calls[0][1].content)
    assert sent["five_cs_metrics"] == FINDINGS["metrics"]
    assert sent["rule_results"] == FINDINGS["rule_results"]
    assert sent["deterministic_route"] == FINDINGS["route_result"]


async def test_markdown_fenced_json_is_still_parsed(monkeypatch):
    fenced = "```json\n" + GOOD_RESPONSE + "\n```"
    llm = _FakeLLM(fenced)
    monkeypatch.setattr(ai_review, "get_llm", lambda agent: llm)

    result = await ai_review.review(**FINDINGS)
    assert result["available"] is True and result["risk_score"] == 42


@pytest.mark.parametrize(
    "raw",
    [
        "not json at all",
        json.dumps({"risk_score": 42}),  # missing required fields is fine — only risk_score is required
    ],
)
async def test_a_risk_score_alone_is_enough_but_garbage_is_not(monkeypatch, raw):
    llm = _FakeLLM(raw)
    monkeypatch.setattr(ai_review, "get_llm", lambda agent: llm)

    result = await ai_review.review(**FINDINGS)
    if raw.startswith("not"):
        assert result["available"] is False and result["error"]
    else:
        # unknown/absent enum fields are nulled out rather than trusted as-is
        assert result["available"] is True
        assert result["risk_score"] == 42
        assert result["risk_band"] is None
        assert result["recommendation"] is None
        assert result["key_risk_factors"] == []


async def test_a_non_numeric_risk_score_is_rejected(monkeypatch):
    llm = _FakeLLM(json.dumps({"risk_score": "very high", "risk_band": "high"}))
    monkeypatch.setattr(ai_review, "get_llm", lambda agent: llm)

    result = await ai_review.review(**FINDINGS)
    assert result["available"] is False
    assert "risk_score" in result["error"]


@pytest.mark.parametrize("out_of_range,expected", [(-15, 0), (137, 100)])
async def test_an_out_of_range_risk_score_is_clamped_not_rejected(monkeypatch, out_of_range, expected):
    llm = _FakeLLM(json.dumps({"risk_score": out_of_range}))
    monkeypatch.setattr(ai_review, "get_llm", lambda agent: llm)

    result = await ai_review.review(**FINDINGS)
    assert result["available"] is True
    assert result["risk_score"] == expected


async def test_a_bogus_recommendation_or_band_is_dropped_not_trusted(monkeypatch):
    llm = _FakeLLM(json.dumps({
        "risk_score": 10, "risk_band": "extremely bad", "recommendation": "auto_approve_immediately",
    }))
    monkeypatch.setattr(ai_review, "get_llm", lambda agent: llm)

    result = await ai_review.review(**FINDINGS)
    assert result["available"] is True
    assert result["risk_band"] is None
    assert result["recommendation"] is None


async def test_transient_server_errors_are_retried_then_succeed(monkeypatch):
    llm = _FakeLLM(ServerError(503, {"message": "overloaded"}), ServerError(503, {"message": "overloaded"}), GOOD_RESPONSE)
    monkeypatch.setattr(ai_review, "get_llm", lambda agent: llm)
    monkeypatch.setattr(ai_review.asyncio, "sleep", lambda *_: _noop())

    result = await ai_review.review(**FINDINGS)
    assert result["available"] is True and result["risk_score"] == 42
    assert len(llm.calls) == 3


async def test_exhausting_all_retries_degrades_instead_of_raising(monkeypatch):
    llm = _FakeLLM(*[ServerError(503, {"message": "down"}) for _ in range(3)])
    monkeypatch.setattr(ai_review, "get_llm", lambda agent: llm)
    monkeypatch.setattr(ai_review.asyncio, "sleep", lambda *_: _noop())

    result = await ai_review.review(**FINDINGS)
    assert result["available"] is False
    assert "unavailable after retries" in result["error"]
    assert len(llm.calls) == 3


async def test_a_missing_api_key_degrades_gracefully(monkeypatch):
    def _raise(agent):
        raise RuntimeError("GEMINI_API_KEY is not set in .env")

    monkeypatch.setattr(ai_review, "get_llm", _raise)

    result = await ai_review.review(**FINDINGS)
    assert result["available"] is False
    assert "GEMINI_API_KEY" in result["error"]
    assert result["risk_score"] is None


async def _noop(*args, **kwargs):
    return None
