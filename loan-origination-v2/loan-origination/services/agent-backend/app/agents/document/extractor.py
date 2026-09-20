import base64
import json
from google.genai.errors import ServerError
import asyncio

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.document.schemas import EXTRACTION_SCHEMAS
from app.core.llm import as_text, get_llm

SYSTEM = """You extract structured data from a financial document image or PDF
for an Australian loan application.

You are told which document type this is meant to be, and given the exact
fields to extract for that type.

Return ONLY a JSON object, no markdown fences, no commentary:
{"matches_claimed_type": true|false, "fields": {"<field_id>": <value or null>},
 "notes": "<optional>"}

Rules:
- If the document clearly is NOT the claimed type (e.g. a bank statement
  submitted as a photo ID), set matches_claimed_type to false, leave fields
  empty, and briefly say what it actually looks like in notes.
- Only extract a field if it is actually visible on the document. Never guess
  or infer a value that isn't shown. Missing is correct; guessed is a
  serious error.
- currency: plain number, no symbols or separators.
- date: YYYY-MM-DD.
- transaction_list fields: an array of {"date": "YYYY-MM-DD", "description": str,
  "amount": number, "direction": "credit"|"debit"}, one entry per line visible
  on the statement.
- text: exactly as written on the document."""


def _parse(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


async def extract(verification_type: str, content: bytes, content_type: str) -> dict:
    fields = EXTRACTION_SCHEMAS.get(verification_type)
    if not fields:
        return {"matches_claimed_type": False, "fields": {}, "notes": f"Unknown document type '{verification_type}'"}

    b64 = base64.b64encode(content).decode("utf-8")
    data_url = f"data:{content_type};base64,{b64}"

    payload = {"claimed_document_type": verification_type, "fields_to_extract": fields}

    llm = get_llm("document")
    messages = [
        SystemMessage(content=SYSTEM),
        HumanMessage(content=[
            {"type": "text", "text": json.dumps(payload, ensure_ascii=False)},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]),
    ]
    last_error = None
    for attempt in range(3):
        try:
            resp = await llm.ainvoke(messages)
            break
        except ServerError as exc:
            last_error = exc
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
    else:
        return {
            "matches_claimed_type": False, "fields": {},
            "notes": f"Extraction service unavailable after retries: {last_error}",
        }

    try:
        parsed = _parse(as_text(resp))
    except (json.JSONDecodeError, IndexError):
        return {"matches_claimed_type": False, "fields": {}, "notes": "extraction failed to parse"}

    return {
        "matches_claimed_type": bool(parsed.get("matches_claimed_type", False)),
        "fields": parsed.get("fields") or {},
        "notes": parsed.get("notes") or "",
    }