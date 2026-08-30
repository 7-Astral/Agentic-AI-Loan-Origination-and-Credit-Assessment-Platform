from typing import Any

from app.agents.interaction.schema import unfilled_required

GROUP_BATCH_SIZE = {
    "expenses": 10,
    # "identity": 3,
    # "household": 3,
    # "employment": 3,
    # "income": 3,
    # "liabilities": 3,
    # "assets": 3,
    # "consent": 2,
    # "confirmation": 1,
}
DEFAULT_BATCH_SIZE = 1


def _sort_key(slot: dict, order: dict[str, int]) -> tuple:
    return (slot["phase"], order[slot["id"]])


def next_batch(
    slots: list[dict],
    filled: dict[str, Any],
    max_size: int | None = None,
) -> list[dict]:
    pending = unfilled_required(slots, filled)
    if not pending:
        return []

    order = {s["id"]: i for i, s in enumerate(slots)}
    pending.sort(key=lambda s: _sort_key(s, order))

    head = pending[0]
    phase, group = head["phase"], head["group"]
    same_group = [s for s in pending if s["phase"] == phase and s["group"] == group]

    cap = max_size or GROUP_BATCH_SIZE.get(group, DEFAULT_BATCH_SIZE)
    return same_group[:cap]


def progress(slots: list[dict], filled: dict[str, Any]) -> dict:
    pending = unfilled_required(slots, filled)
    answered = len([s for s in slots if s["id"] in filled])
    return {
        "answered": answered,
        "remaining_known": len(pending),
        "current_phase": pending[0]["phase"] if pending else None,
        "complete": not pending,
    }


def commit(
    filled: dict[str, Any],
    provenance: dict[str, dict],
    slot_id: str,
    value: Any,
    source: str,
    turn: int,
) -> None:
    filled[slot_id] = value
    provenance[slot_id] = {"source": source, "turn": turn}