import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import as_text, get_llm

SYSTEM = """You extract structured values from what a loan applicant said.

You are given the fields currently being asked about and the applicant's reply.
Return ONLY a JSON object, no markdown fences, no commentary, with this shape:

{"values": {"<field_id>": <value>}, "unclear": ["<field_id>"], "notes": "<optional>"}

Rules:
- Only include a field in "values" if the applicant stated it in this reply.
- NEVER infer, estimate, or calculate a value they did not give. If they did
  not say it, leave it out. A missing field is correct; a guessed field is a
  serious error.
- Put a field in "unclear" if they addressed it but ambiguously.
- If they gave a value for a field NOT in the list, include it anyway using
  that field's id if you can identify it from the list. Otherwise ignore it.
- currency and number: return a plain number, no symbols or separators.
- boolean: return true or false.
- choice: return exactly one of the listed options.
- date: return YYYY-MM-DD.
- text: return everything they stated about that field, in full — do not
  shorten, drop qualifying words, or reduce a multi-word answer to a single
  term. "Toyota Corolla hybrid" must be returned as "Toyota Corolla hybrid",
  not "Corolla". "Lightly cleaned" means fixing casing/spacing only, never
  trimming content.
- If the applicant asked a question instead of answering, return empty values
  and put what they asked in "notes"."""


def _field_spec(slot: dict) -> dict:
    spec = {"id": slot["id"], "label": slot["label"], "type": slot["type"]}
    if slot.get("ask_hint"):
        spec["guidance"] = slot["ask_hint"]
    if slot.get("options"):
        spec["options"] = slot["options"]
    return spec


def _parse(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


async def extract(
    batch: list[dict],
    reply: str,
    all_slots: list[dict] | None = None,
) -> dict[str, Any]:
    """Extract slot values from an applicant reply."""
    visible = all_slots or batch
    prompt = {
        "fields_asked": [_field_spec(s) for s in batch],
        "other_known_fields": [
            _field_spec(s) for s in visible if s not in batch
        ][:60],
        "applicant_reply": reply,
    }

    llm = get_llm("interaction")
    resp = await llm.ainvoke(
        [SystemMessage(content=SYSTEM),
         HumanMessage(content=json.dumps(prompt, ensure_ascii=False))]
    )

    try:
        parsed = _parse(as_text(resp))
    except (json.JSONDecodeError, IndexError):
        return {"values": {}, "unclear": [s["id"] for s in batch],
                "notes": "extraction failed to parse"}

    return {
        "values": parsed.get("values") or {},
        "unclear": parsed.get("unclear") or [],
        "notes": parsed.get("notes") or "",
    }