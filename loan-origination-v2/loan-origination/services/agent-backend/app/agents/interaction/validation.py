from datetime import date
from typing import Any

TRUTHY = {"yes", "y", "true", "t", "1", "correct", "yep", "yeah"}
FALSY = {"no", "n", "false", "f", "0", "nope", "nah"}


class ValidationError(ValueError):
    pass


def _to_number(value: Any) -> float:
    if isinstance(value, bool):
        raise ValidationError("expected a number, got true/false")
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace("$", "").replace(",", "").strip().lower()
    for suffix, mult in (("k", 1_000), ("m", 1_000_000)):
        if cleaned.endswith(suffix):
            cleaned = cleaned[:-1]
            return float(cleaned) * mult
    return float(cleaned)


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in TRUTHY:
        return True
    if text in FALSY:
        return False
    raise ValidationError("expected yes or no")


def _age_on(dob: date, today: date) -> int:
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


def validate(slot: dict, value: Any, today: date | None = None) -> Any:
   
    if value is None:
        raise ValidationError("no value provided")

    rules = slot.get("validation") or {}
    slot_type = slot["type"]

    if slot_type in ("currency", "number"):
        try:
            number = _to_number(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"could not read {value!r} as a number") from exc
        if "min" in rules and number < rules["min"]:
            raise ValidationError(f"must be at least {rules['min']:,}")
        if "max" in rules and number > rules["max"]:
            raise ValidationError(f"must be no more than {rules['max']:,}")
        return number

    if slot_type == "boolean":
        return _to_bool(value)

    if slot_type == "choice":
        text = str(value).strip().lower().replace(" ", "_").replace("-", "_")
        options = slot.get("options") or []
        for opt in options:
            if opt.lower() == text:
                return opt
        raise ValidationError(f"must be one of: {', '.join(options)}")

    if slot_type == "date":
        try:
            parsed = date.fromisoformat(str(value).strip())
        except ValueError as exc:
            raise ValidationError("expected a date as YYYY-MM-DD") from exc
        if "min_age" in rules:
            age = _age_on(parsed, today or date.today())
            if age < rules["min_age"]:
                raise ValidationError(
                    f"applicant must be at least {rules['min_age']}"
                )
        return parsed.isoformat()
    
    if slot_type == "address":
        text = str(value).strip()
        if len(text) < 8 or not any(ch.isdigit() for ch in text):
            raise ValidationError(
                "needs a full street address including the street number"
            )
        return text

    text = str(value).strip()
    if not text:
        raise ValidationError("cannot be empty")
    return text