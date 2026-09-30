"""Pure logic tests for the interview slot machinery — no DB, no LLM, no
HTTP. These are the deterministic rules everything else (extraction,
batching, questions) is built on top of."""
from datetime import date

import pytest

from app.agents.interaction.resolver import next_batch, progress
from app.agents.interaction.schema import is_required, unfilled_required
from app.agents.interaction.validation import ValidationError, validate


# ------------------------------------------------------------- validate() --

def test_currency_accepts_plain_and_formatted_values():
    slot = {"type": "currency", "validation": {}}
    assert validate(slot, 5000) == 5000.0
    assert validate(slot, "5000") == 5000.0
    assert validate(slot, "$5,000") == 5000.0
    assert validate(slot, "5k") == 5000.0
    assert validate(slot, "1.5m") == 1_500_000.0


def test_currency_enforces_min_and_max():
    slot = {"type": "currency", "validation": {"min": 1000, "max": 5000}}
    with pytest.raises(ValidationError):
        validate(slot, 500)
    with pytest.raises(ValidationError):
        validate(slot, 6000)
    assert validate(slot, 2500) == 2500.0


def test_currency_rejects_boolean_and_garbage():
    slot = {"type": "currency", "validation": {}}
    with pytest.raises(ValidationError):
        validate(slot, True)
    with pytest.raises(ValidationError):
        validate(slot, "not a number")


def test_boolean_accepts_common_yes_no_variants():
    slot = {"type": "boolean"}
    for truthy in ("yes", "Y", "true", "1", "correct", "yep"):
        assert validate(slot, truthy) is True
    for falsy in ("no", "N", "false", "0", "nope"):
        assert validate(slot, falsy) is False
    with pytest.raises(ValidationError):
        validate(slot, "maybe")


def test_choice_matches_case_and_separator_insensitively():
    slot = {"type": "choice", "options": ["debt_consolidation", "car", "other"]}
    assert validate(slot, "Debt Consolidation") == "debt_consolidation"
    assert validate(slot, "debt-consolidation") == "debt_consolidation"
    with pytest.raises(ValidationError):
        validate(slot, "vacation")


def test_date_enforces_min_age():
    slot = {"type": "date", "validation": {"min_age": 18}}
    assert validate(slot, "2000-01-01", today=date(2024, 6, 1)) == "2000-01-01"
    with pytest.raises(ValidationError):
        validate(slot, "2010-01-01", today=date(2024, 6, 1))


def test_date_rejects_bad_format():
    slot = {"type": "date"}
    with pytest.raises(ValidationError):
        validate(slot, "not-a-date")


def test_address_requires_street_number_and_min_length():
    slot = {"type": "address"}
    assert validate(slot, "42 Example Street, Melbourne") == "42 Example Street, Melbourne"
    with pytest.raises(ValidationError):
        validate(slot, "Melbourne")  # no digit
    with pytest.raises(ValidationError):
        validate(slot, "1 St")  # too short


def test_text_rejects_empty():
    slot = {"type": "text"}
    assert validate(slot, "  hello  ") == "hello"
    with pytest.raises(ValidationError):
        validate(slot, "   ")


def test_none_value_always_rejected():
    with pytest.raises(ValidationError):
        validate({"type": "text"}, None)


# ------------------------------------------------------- is_required() ----

def test_required_defaults_true():
    assert is_required({"id": "a"}, {}) is True


def test_required_false_when_flag_set():
    assert is_required({"id": "a", "required": False}, {}) is False


def test_required_when_expression_evaluated_against_filled():
    slot = {"id": "spouse_income", "required_when": "has_spouse == True"}
    assert is_required(slot, {"has_spouse": True}) is True
    assert is_required(slot, {"has_spouse": False}) is False


def test_required_when_missing_dependency_is_unknown():
    """A required_when expression referencing a not-yet-filled field can't
    be evaluated yet — treated as unknown (None), not required or skippable."""
    slot = {"id": "spouse_income", "required_when": "has_spouse == True"}
    assert is_required(slot, {}) is None


def test_unfilled_required_excludes_already_filled_and_not_required():
    slots = [
        {"id": "a", "required": True},
        {"id": "b", "required": False},
        {"id": "c", "required": True},
    ]
    assert [s["id"] for s in unfilled_required(slots, {"c": "x"})] == ["a"]


# ------------------------------------------------------------ next_batch --

def test_next_batch_respects_default_size_of_one():
    slots = [
        {"id": "a", "phase": 1, "group": "details", "required": True},
        {"id": "b", "phase": 1, "group": "details", "required": True},
    ]
    batch = next_batch(slots, {})
    assert [s["id"] for s in batch] == ["a"]  # not both — default cap is 1


def test_next_batch_groups_expenses_up_to_ten():
    slots = [{"id": f"e{i}", "phase": 1, "group": "expenses", "required": True} for i in range(12)]
    batch = next_batch(slots, {})
    assert len(batch) == 10


def test_next_batch_picks_earliest_phase_first():
    slots = [
        {"id": "later", "phase": 2, "group": "g", "required": True},
        {"id": "earlier", "phase": 1, "group": "g", "required": True},
    ]
    batch = next_batch(slots, {})
    assert [s["id"] for s in batch] == ["earlier"]


def test_next_batch_empty_when_everything_filled():
    slots = [{"id": "a", "phase": 1, "group": "g", "required": True}]
    assert next_batch(slots, {"a": 1}) == []


# ------------------------------------------------------------- progress --

def test_progress_reports_answered_and_remaining():
    slots = [
        {"id": "a", "phase": 1, "group": "g", "required": True},
        {"id": "b", "phase": 1, "group": "g", "required": True},
    ]
    p = progress(slots, {"a": 1})
    assert p["answered"] == 1
    assert p["remaining_known"] == 1
    assert p["current_phase"] == 1
    assert p["complete"] is False


def test_progress_complete_when_nothing_pending():
    slots = [{"id": "a", "phase": 1, "group": "g", "required": True}]
    p = progress(slots, {"a": 1})
    assert p["complete"] is True
    assert p["current_phase"] is None
