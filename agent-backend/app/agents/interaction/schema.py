from typing import Any


class SlotConditionError(ValueError):


def is_required(slot: dict, filled: dict[str, Any]) -> bool | None:
    if not slot.get("required", True) and not slot.get("required_when"):
        return False

    expr = slot.get("required_when")
    if not expr:
        return True

    try:
        return bool(eval(expr, {"__builtins__": {}}, dict(filled)))
    except (NameError, TypeError):
        return None
    except Exception as exc:
        raise SlotConditionError(f"{slot['id']}: {expr!r} -> {exc}") from exc


def unfilled_required(schema_slots: list[dict], filled: dict[str, Any]) -> list[dict]:
    return [
        s
        for s in schema_slots
        if s["id"] not in filled and is_required(s, filled) is True
    ]