"""LLM final-risk-score review — the one step in the Five C's pipeline that is
actually AI, layered on top of (never inside) the deterministic engine.

`run.py` computes every Five C's metric and runs the rules engine entirely in
plain code first — nothing about a metric's value or the rule/route outcome
ever comes from a model. Only once that's finished does this module hand the
*already-computed* findings to the LLM and ask it for one thing: a holistic
final risk score and recommendation, the way a senior credit analyst would
read a completed assessment pack rather than re-deriving the numbers
themselves. The model never sees raw declared answers or documents, and it
is explicitly told it cannot use anything not already in the findings —
matching the same "unavailable is honest, guessed is a serious error" rule
`character.py`/`bureau_mock.py` already hold the deterministic side to.

This call is additive and best-effort: if `GEMINI_API_KEY` is unset, the
service is unreachable, or the response can't be parsed, `review()` degrades
to `{"available": False, ...}` rather than raising — a Gemini outage must
never take down the deterministic assessment `run_retail_assessment` still
returns. Same retry-on-`ServerError` pattern as `agents/document/extractor.py`.
"""

import json

from google.genai.errors import ServerError
import asyncio

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import as_text, get_llm

# Deliberately the SAME vocabulary as agents.assessment.rules.engine.route()'s `tier` —
# the model's recommendation is comparable to the deterministic route at a glance, but it
# is a second, independent opinion for a human to weigh, never a replacement for it.
RECOMMENDATIONS = ("auto_eligible", "conditional", "underwriter_review", "decline_recommended")
RISK_BANDS = ("low", "medium", "high", "very_high")

SYSTEM = """You are a senior credit risk analyst at an Australian bank, reviewing a
completed Five C's credit assessment pack for a retail loan application. The pack was
produced entirely by deterministic code: every metric was calculated from the
applicant's declared answers and verified documents, and every rule/route outcome was
evaluated by a rules engine. Nothing in it was estimated or guessed by anyone.

Your job is narrow: read the pack and give ONE holistic final risk assessment — you are
not recalculating any metric, and you must not introduce a fact, number or document that
is not already present in the pack given to you.

Return ONLY a JSON object, no markdown fences, no commentary, in exactly this shape:
{
  "risk_score": <integer 0-100, where 0 = negligible risk and 100 = certain default>,
  "risk_band": "low" | "medium" | "high" | "very_high",
  "recommendation": "auto_eligible" | "conditional" | "underwriter_review" | "decline_recommended",
  "key_risk_factors": ["<short phrase>", ...],
  "key_strengths": ["<short phrase>", ...],
  "rationale": "<2-4 sentences a credit manager could read on its own>"
}

Rules:
- Every metric has a "state": "computed" ones have a usable value; "unavailable" or
  "not_applicable" ones do not, and their absence is itself information (e.g. no bureau
  file, no collateral offered) — never treat a missing metric as zero, pass, or fail.
  Say so in your rationale if a real gap in the evidence limits your confidence.
- The rule engine's own "route" (auto_eligible / conditional / underwriter_review /
  decline_recommended) is a strict deterministic floor: if it is decline_recommended or
  underwriter_review, your recommendation must be at least that strict — you may be
  stricter than the rule route based on the full picture, but never more lenient than a
  rule the applicant has already failed or flagged.
- credit_score under "character" may be tagged "derived"/"mock estimate" rather than a
  real bureau pull — weigh it accordingly and say so as a limitation, not as if it were a
  verified bureau file.
- Ground every risk factor and strength in a specific named metric or rule result from
  the pack. Do not invent a concern that isn't traceable to something you were given.
- Keep key_risk_factors and key_strengths concise phrases (a handful of words each), most
  important first; empty lists are fine if there's genuinely nothing to list."""


def _parse(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _unavailable(reason: str) -> dict:
    return {
        "available": False,
        "risk_score": None,
        "risk_band": None,
        "recommendation": None,
        "key_risk_factors": [],
        "key_strengths": [],
        "rationale": None,
        "error": reason,
    }


def _findings_payload(
    *,
    product_code: str,
    loan_amount: float | None,
    loan_term_months: int | None,
    metrics: dict,
    rule_results: list[dict],
    route_result: dict,
) -> dict:
    return {
        "product_code": product_code,
        "loan_amount": loan_amount,
        "loan_term_months": loan_term_months,
        "five_cs_metrics": metrics,
        "rule_results": rule_results,
        "deterministic_route": route_result,
    }


async def review(
    *,
    product_code: str,
    loan_amount: float | None,
    loan_term_months: int | None,
    metrics: dict,
    rule_results: list[dict],
    route_result: dict,
) -> dict:
    """Sends the already-computed Five C's findings to the LLM and returns its final risk
    review. Never raises — a failure at any stage (no key, unreachable, bad JSON) comes
    back as `{"available": False, "error": "..."}` instead."""
    try:
        llm = get_llm("assessment")
    except RuntimeError as exc:
        return _unavailable(str(exc))

    payload = _findings_payload(
        product_code=product_code,
        loan_amount=loan_amount,
        loan_term_months=loan_term_months,
        metrics=metrics,
        rule_results=rule_results,
        route_result=route_result,
    )
    messages = [
        SystemMessage(content=SYSTEM),
        HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
    ]

    last_error: Exception | None = None
    resp = None
    for attempt in range(3):
        try:
            resp = await llm.ainvoke(messages)
            break
        except ServerError as exc:
            last_error = exc
            if attempt < 2:
                await asyncio.sleep(2**attempt)
    if resp is None:
        return _unavailable(f"AI review unavailable after retries: {last_error}")

    try:
        parsed = _parse(as_text(resp))
    except (json.JSONDecodeError, IndexError) as exc:
        return _unavailable(f"AI review response could not be parsed: {exc}")

    risk_score = parsed.get("risk_score")
    if not isinstance(risk_score, (int, float)):
        return _unavailable("AI review did not return a numeric risk_score")
    risk_score = max(0, min(100, round(float(risk_score))))

    risk_band = parsed.get("risk_band")
    if risk_band not in RISK_BANDS:
        risk_band = None

    recommendation = parsed.get("recommendation")
    if recommendation not in RECOMMENDATIONS:
        recommendation = None

    return {
        "available": True,
        "risk_score": risk_score,
        "risk_band": risk_band,
        "recommendation": recommendation,
        "key_risk_factors": [str(x) for x in (parsed.get("key_risk_factors") or [])],
        "key_strengths": [str(x) for x in (parsed.get("key_strengths") or [])],
        "rationale": parsed.get("rationale") or "",
        "error": None,
    }
