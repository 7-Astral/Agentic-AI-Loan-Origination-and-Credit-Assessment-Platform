from fastapi.testclient import TestClient

import agents.risk_assessment.orchestrator as orchestrator_module
from core.database import engine
from integration.abr import AbrResult
from integration.credit_bureau import CreditBureauResult
from main import app
from scripts.seed import seed


async def _fake_get_credit_report(name: str, dob: str, address: str) -> CreditBureauResult:
    return CreditBureauResult(matched=False)


async def _fake_lookup_abn(abn: str) -> AbrResult:
    return AbrResult(found=None, error="no_guid")


class _patched_collectors:
    """The router calls the orchestrator without injected collectors, so it resolves the
    real integration.* functions (bound at orchestrator import time). Swapping those bound
    names for the duration of a test keeps this API-level test fully offline, per the
    no-network-requests rule, without relying on any mocking library."""

    def __enter__(self) -> None:
        self._original_bureau = orchestrator_module._default_get_credit_report
        self._original_abr = orchestrator_module._default_lookup_abn
        orchestrator_module._default_get_credit_report = _fake_get_credit_report
        orchestrator_module._default_lookup_abn = _fake_lookup_abn

    def __exit__(self, *exc: object) -> None:
        orchestrator_module._default_get_credit_report = self._original_bureau
        orchestrator_module._default_lookup_abn = self._original_abr


async def test_post_risk_assessment_returns_report_for_unmatched_identity() -> None:
    with _patched_collectors():
        await seed()
        await engine.dispose()

        with TestClient(app) as client:
            response = client.post(
                "/risk-assessment",
                json={
                    "application": {
                        "applicant": {"name": "Someone", "dob": "1990-01-01", "address": "x"}
                    }
                },
            )

    assert response.status_code == 200
    body = response.json()
    assert body["five_cs"]["character"]["source"] == "unavailable"
    assert body["five_cs"]["character"]["value"] is None
    assert "application_id" in body


async def test_post_risk_assessment_echoes_supplied_application_id() -> None:
    with _patched_collectors():
        await seed()
        await engine.dispose()

        with TestClient(app) as client:
            response = client.post(
                "/risk-assessment", json={"application_id": "app-123", "application": {}}
            )

    assert response.status_code == 200
    assert response.json()["application_id"] == "app-123"


async def test_post_risk_assessment_empty_body_still_succeeds() -> None:
    with _patched_collectors():
        await seed()
        await engine.dispose()

        with TestClient(app) as client:
            response = client.post("/risk-assessment", json={})

    assert response.status_code == 200
