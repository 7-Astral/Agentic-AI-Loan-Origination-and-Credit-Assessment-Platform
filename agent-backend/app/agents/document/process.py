from typing import Any

from app.agents.document.categorize import categorize_transactions
from app.agents.document.extractor import extract
from app.agents.document.reconcile import reconcile


async def process_document(
    verification_type: str, content: bytes, content_type: str, filled: dict[str, Any], categorize: bool = True
) -> dict:
    result = await extract(verification_type, content, content_type)
    if not result["matches_claimed_type"]:
        return {**result, "verifications": []}

    fields = result["fields"]
    if categorize and verification_type == "bank_statements" and fields.get("transactions"):
        fields["transactions"] = await categorize_transactions(fields["transactions"])
    return {**result, "verifications": reconcile(verification_type, fields, filled)}
