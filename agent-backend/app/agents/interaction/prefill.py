import logging
from typing import Any

import httpx

from app.agents.interaction.validation import ValidationError, validate
from app.services.core_banking import core_banking

logger = logging.getLogger(__name__)

PROFILE_FIELDS = {
    "full_name": "full_name",
    "email_address": "email",
    "mobile_number": "phone",
    "date_of_birth": "date_of_birth",
    "current_address": "address",
}


def prefill_from_profile(slots: list[dict], profile: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict]]:
    filled: dict[str, Any] = {}
    provenance: dict[str, dict] = {}
    for slot in slots:
        field = PROFILE_FIELDS.get(slot["id"])
        value = profile.get(field) if field else None
        if value in (None, ""):
            continue
        try:
            filled[slot["id"]] = validate(slot, value)
        except ValidationError:
            continue
        provenance[slot["id"]] = {"source": "profile", "turn": 0}
    return filled, provenance


async def load_profile_prefill(
    customer_id: str | None, slots: list[dict]
) -> tuple[dict[str, Any], dict[str, dict]]:
    if not customer_id:
        return {}, {}
    try:
        profile = await core_banking.get_customer_profile(customer_id)
    except httpx.HTTPError as exc:
        logger.warning("Could not load customer profile for prefill: %s", exc)
        return {}, {}
    return prefill_from_profile(slots, profile)
