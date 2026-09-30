
import pytest

from app.agents.interaction import graph
from mock_core_banking.slots.registry import schema_for

INCOME_SLOTS = ("gross_annual_income", "net_income_amount", "net_income_frequency")


def _slots(*ids):
    return [s for s in schema_for("PERSONAL-TEST")["slots"] if s["id"] in ids]


async def _ingest(monkeypatch, asked, values, filled):
    async def fake_extract(batch, reply, all_slots=None):
        return {"values": values, "unclear": [], "notes": ""}

    monkeypatch.setattr(graph, "extract", fake_extract)
    batch = _slots(*asked)
    return await graph.ingest_node({
        "current_batch": batch,
        "slots": _slots(*INCOME_SLOTS),
        "transcript": [{"role": "user", "content": "..."}],
        "turn": 5,
        "filled": filled,
    })


async def test_yearly_take_home_answered_as_weekly_is_refused(monkeypatch):
  
    result = await _ingest(
        monkeypatch, ["net_income_frequency"], {"net_income_frequency": "weekly"},
        {"gross_annual_income": 60000, "net_income_amount": 50000},
    )
    assert "net_income_frequency" not in result["filled"]
    assert result["repair"] is True
    assert "2,600,000" in result["last_error"] and "60,000" in result["last_error"]


async def test_amount_with_its_frequency_fills_both(monkeypatch):
    result = await _ingest(
        monkeypatch, ["net_income_amount"], {"net_income_amount": {"amount": 50000, "frequency": "annually"}},
        {"gross_annual_income": 60000},
    )
    assert result["filled"]["net_income_amount"] == 50000
    assert result["filled"]["net_income_frequency"] == "annually"
    assert result["last_error"] is None


async def test_amount_is_re_expressed_in_a_known_pay_cycle(monkeypatch):
    result = await _ingest(
        monkeypatch, ["net_income_amount"], {"net_income_amount": {"amount": 50000, "frequency": "annually"}},
        {"gross_annual_income": 60000, "net_income_frequency": "weekly"},
    )
    assert result["filled"]["net_income_amount"] == pytest.approx(961.54)
    assert result["provenance"]["net_income_amount"]["stated"] == {"amount": 50000, "frequency": "annually"}


async def test_gross_income_given_weekly_is_stored_yearly(monkeypatch):
    result = await _ingest(
        monkeypatch, ["gross_annual_income"], {"gross_annual_income": {"amount": 1150, "frequency": "weekly"}}, {},
    )
    assert result["filled"]["gross_annual_income"] == pytest.approx(59800)


async def test_plausible_take_home_is_accepted(monkeypatch):
    result = await _ingest(
        monkeypatch, ["net_income_amount", "net_income_frequency"],
        {"net_income_amount": {"amount": 1923, "frequency": "fortnightly"}},
        {"gross_annual_income": 60000},
    )
    assert result["filled"]["net_income_amount"] == 1923
    assert result["filled"]["net_income_frequency"] == "fortnightly"
    assert result["last_error"] is None
