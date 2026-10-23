from typing import Any

from app.core import observability
from app.agents.document.business_cashflow import summarise_business_cashflow
from app.agents.document.categorize import categorize_transactions
from app.agents.document.extractor import extract
from app.agents.document.reconcile import reconcile


@observability.traced("document-agent", as_type="agent", omit=("content",))
async def process_document(
    verification_type: str, content: bytes, content_type: str, filled: dict[str, Any],
    categorize: bool = True, loan_type: str | None = None,
) -> dict:
    result = await extract(verification_type, content, content_type)
    observability.annotate(verification_type=verification_type, method=result.get("method"), bytes=len(content))
    observability.score(f"document.{verification_type}.matches_claimed_type", bool(result["matches_claimed_type"]))
    if not result["matches_claimed_type"]:
        return {**result, "verifications": []}

    business = loan_type == "business"
    fields = result["fields"]
    if categorize and verification_type == "bank_statements" and fields.get("transactions"):
        fields["transactions"] = await categorize_transactions(fields["transactions"], business=business)
        if business:
            fields.update(summarise_business_cashflow(fields))
    verifications = reconcile(verification_type, fields, filled, loan_type=loan_type)
    checked = [v for v in verifications if v["status"] in ("match", "mismatch", "missing")]
    if checked:
        matched = sum(v["status"] == "match" for v in checked)
        observability.score(
            f"document.{verification_type}.match_rate", matched / len(checked),
            comment=", ".join(f'{v["slot_id"]}={v["status"]}' for v in checked),
        )
    return {**result, "verifications": verifications}
