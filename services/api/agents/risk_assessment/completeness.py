from typing import Any

from schemas.application import NormalizedApplication
from schemas.risk_assessment import MissingField, RequiredField


def _get_by_path(data: dict[str, Any], path: str) -> Any:
    node: Any = data
    for part in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def compute_missing_fields(
    normalized: NormalizedApplication, required_fields: list[RequiredField]
) -> list[MissingField]:
    """Diffs the normalised application against `required_fields` (a per-product checklist,
    see checklist_loader.py). `field.key` is a dotted path into the normalised application,
    e.g. "applicant.employment.income"."""
    data = normalized.model_dump(mode="json")
    missing: list[MissingField] = []
    for field in required_fields:
        if not _is_present(_get_by_path(data, field.key)):
            missing.append(
                MissingField(
                    field=field.key,
                    label=field.label,
                    five_c=field.five_c,
                    requirement=field.requirement,
                )
            )
    return missing


def compute_completeness_score(
    required_fields: list[RequiredField], missing_fields: list[MissingField]
) -> float:
    if not required_fields:
        return 1.0
    present = len(required_fields) - len(missing_fields)
    return round(present / len(required_fields), 4)
