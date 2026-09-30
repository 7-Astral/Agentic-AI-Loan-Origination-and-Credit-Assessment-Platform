import asyncio
import logging
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import as_text, get_llm

SYSTEM = """You write a short, plain-English note for a credit officer reviewing
a loan application. You are given the already-computed weighted 5C score
breakdown and decision tier for this application — you do not decide
anything, you only explain it clearly.

Write 3-5 sentences, no headings, no bullet points, no markdown. Mention the
overall score and tier, the strongest and weakest of the five Cs by name, and
one specific number that explains why. Do not invent any figure not given to
you. Do not recommend an action beyond what the tier already implies."""

TIMEOUT_SECONDS = 8
QUOTA_BACKOFF_SECONDS = 300
_quiet_until = 0.0

logger = logging.getLogger(__name__)


LEGACY_TEMPLATE_NOTE = "This is a summary — the AI narrative was unavailable when this report was generated."


def is_template(text: str | None) -> bool:
    return bool(text) and text.rstrip().endswith(LEGACY_TEMPLATE_NOTE)


def _template_narrative(score_report: dict, product_name: str | None) -> str:
    groups = score_report["group_scores"]
    computed = {name: g["score"] for name, g in groups.items() if g["state"] == "computed" and g["score"] is not None}
    tier_text = (score_report["tier"] or "").replace("_", " ")
    product_text = f" for the {product_name}" if product_name else ""

    if not computed:
        return (
            f"Overall weighted score {score_report['overall_score']}/100{product_text}, "
            f"recommended tier: {tier_text}. Not enough evidence was available yet to "
            f"break this down by individual C."
        )

    best = max(computed, key=lambda k: computed[k])
    worst = min(computed, key=lambda k: computed[k])
    return (
        f"Overall weighted score {score_report['overall_score']}/100{product_text}, "
        f"recommended tier: {tier_text}. {best.capitalize()} was the strongest area at "
        f"{computed[best]:.0f}/100, while {worst.capitalize()} was the weakest at "
        f"{computed[worst]:.0f}/100."
    )


async def generate_narrative(score_report: dict, product: dict[str, Any] | None) -> tuple[str, bool]:
    product_name = (product or {}).get("name")
    payload = {
        "product": product_name,
        "overall_score": score_report["overall_score"],
        "tier": score_report["tier"],
        "group_scores": {
            name: g["score"] for name, g in score_report["group_scores"].items() if g["state"] == "computed"
        },
        "data_completeness": score_report["data_completeness"],
    }

    global _quiet_until
    if time.monotonic() < _quiet_until:
        return _template_narrative(score_report, product_name), False

    try:
        llm = get_llm("assessment", max_retries=1)
        messages = [
            SystemMessage(content=SYSTEM),
            HumanMessage(content=str(payload)),
        ]
        resp = await asyncio.wait_for(llm.ainvoke(messages), timeout=TIMEOUT_SECONDS)
        text = as_text(resp)
        if text:
            return text, True
        logger.warning("Narrative model returned no text; using the template summary")
    except asyncio.TimeoutError:
        logger.warning("Narrative model timed out after %ss; using the template summary", TIMEOUT_SECONDS)
    except Exception as exc:
        if "RESOURCE_EXHAUSTED" in str(exc) or "429" in str(exc):
            _quiet_until = time.monotonic() + QUOTA_BACKOFF_SECONDS
        logger.warning("Narrative model failed (%s: %s); using the template summary", type(exc).__name__, str(exc)[:200])

    return _template_narrative(score_report, product_name), False


async def get_or_generate_narrative(
    score_report: dict, product: dict[str, Any] | None,
    prior_overall_score: float | None, prior_narrative: str | None,
) -> tuple[str, bool]:
    reusable = prior_narrative and not is_template(prior_narrative)
    if reusable and prior_overall_score is not None and prior_overall_score == score_report["overall_score"]:
        return prior_narrative, True
    return await generate_narrative(score_report, product)
