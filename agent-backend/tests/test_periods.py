
from decimal import Decimal

import pytest

from app.agents.interaction import graph
from app.agents.interaction.periods import normalise_frequency, read_stated_amount, to_monthly
from mock_core_banking.slots.registry import schema_for


@pytest.mark.parametrize(
    "amount, frequency, expected",
    [
        (400, "weekly", Decimal("1733.33")),  # 400 x 52 / 12, not 400 x 4
        (400, "fortnightly", Decimal("866.67")),
        (400, "monthly", Decimal("400.00")),
        (400, "quarterly", Decimal("133.33")),
        (1200, "annually", Decimal("100.00")),
        (400, None, Decimal("400.00")),  # no frequency given: answered as asked (monthly)
        ("150.50", "weekly", Decimal("652.17")),
    ],
)
def test_to_monthly(amount, frequency, expected):
    assert to_monthly(amount, frequency) == expected


def test_frequency_aliases():
    assert normalise_frequency("a week") == "weekly"
    assert normalise_frequency("Fortnight") == "fortnightly"
    assert normalise_frequency("yearly") == "annually"
    assert normalise_frequency("sometimes") is None
    assert normalise_frequency(None) is None


def test_read_stated_amount_accepts_object_or_bare_number():
    assert read_stated_amount({"amount": 400, "frequency": "weekly"}) == (400, "weekly")
    assert read_stated_amount(250) == (250, None)


def test_expense_and_repayment_slots_are_marked_per_month():
    per_month = {s["id"] for s in schema_for("PERSONAL-TEST")["slots"] if s.get("per_month")}
    assert "exp_rent_board" in per_month
    assert "exp_food_groceries" in per_month
    assert "other_loan_repayments_monthly" in per_month
    assert "gross_annual_income" not in per_month


async def test_ingest_converts_weekly_expense_to_monthly(monkeypatch):
    slots = [s for s in schema_for("PERSONAL-TEST")["slots"] if s["id"] in ("exp_rent_board", "exp_phone_internet_media")]

    async def fake_extract(batch, reply, all_slots=None):
        return {
            "values": {
                "exp_rent_board": {"amount": 400, "frequency": "weekly"},
                "exp_phone_internet_media": {"amount": 80, "frequency": "monthly"},
            },
            "unclear": [],
            "notes": "",
        }

    monkeypatch.setattr(graph, "extract", fake_extract)
    state = {
        "current_batch": slots,
        "slots": slots,
        "transcript": [{"role": "user", "content": "Rent is $400 a week and my phone is $80 a month"}],
        "turn": 3,
        "filled": {},
    }
    result = await graph.ingest_node(state)

    assert result["filled"]["exp_rent_board"] == pytest.approx(1733.33)
    assert result["filled"]["exp_phone_internet_media"] == pytest.approx(80)
    # What they actually said is kept alongside the converted figure.
    assert result["provenance"]["exp_rent_board"]["stated"] == {"amount": 400, "frequency": "weekly"}
    assert "stated" not in result["provenance"]["exp_phone_internet_media"]
