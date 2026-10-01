from typing import Any

from app.agents.interaction.extractor import extract
from app.agents.interaction.graph import _income_conflict, _pair_with_frequency
from app.agents.interaction.periods import read_stated_amount, to_annual, to_monthly
from app.agents.interaction.validation import ValidationError, validate

INCOME_SLOTS = ("gross_annual_income", "net_income_amount", "net_income_frequency")


async def apply_correction(state: dict, message: str) -> dict[str, Any]:
    slots = state["slots"]
    filled = state.get("filled") or {}
    turn = state.get("turn", 0) + 1
    by_id = {s["id"]: s for s in slots}

    answered = [s for s in slots if s["id"] in filled]
    result = await extract(answered, message, slots)

    changed: dict[str, Any] = {}
    provenance: dict[str, dict] = {}
    errors: list[str] = []

    for slot_id, raw in (result.get("values") or {}).items():
        slot = by_id.get(slot_id)
        if slot is None:
            continue
        stated = None
        if slot.get("per_month") or slot.get("per_year"):
            amount, frequency = read_stated_amount(raw)
            basis = "monthly" if slot.get("per_month") else "annually"
            try:
                raw = float(to_monthly(amount, frequency) if basis == "monthly" else to_annual(amount, frequency))
            except (ArithmeticError, TypeError, ValueError):
                raw = amount
            if frequency and frequency != basis:
                stated = {"amount": amount, "frequency": frequency}
        elif slot.get("frequency_slot"):
            raw, stated = _pair_with_frequency(slot, raw, filled, changed, provenance, by_id, turn)
        try:
            value = validate(slot, raw)
        except ValidationError as exc:
            errors.append(f"{slot['label']}: {exc}")
            continue
        if filled.get(slot_id) == value:
            continue
        changed[slot_id] = value
        provenance[slot_id] = {"source": "corrected", "turn": turn}
        if stated:
            provenance[slot_id]["stated"] = stated

    touches_income = any(slot_id in changed for slot_id in INCOME_SLOTS)
    conflict = _income_conflict({**filled, **changed}) if touches_income else None
    if conflict:
        for slot_id in INCOME_SLOTS:
            changed.pop(slot_id, None)
            provenance.pop(slot_id, None)
        errors.append(conflict)

    return {
        "changed": changed,
        "previous": {slot_id: filled.get(slot_id) for slot_id in changed},
        "provenance": provenance,
        "errors": errors,
        "turn": turn,
    }
