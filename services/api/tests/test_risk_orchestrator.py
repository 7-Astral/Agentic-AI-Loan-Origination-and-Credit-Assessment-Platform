from agents.risk_assessment.orchestrator import assess_application
from core.database import AsyncSessionLocal
from integration.abr import AbrResult
from integration.credit_bureau import CreditBureauResult
from scripts.seed import seed


def _matched_bureau(score: int = 742, band: str = "good"):
    async def fn(name: str, dob: str, address: str) -> CreditBureauResult:
        return CreditBureauResult(
            matched=True,
            score=score,
            band=band,
            report_summary={"enquiries_last_6_months": 2, "adverse_events": 0},
        )

    return fn


def _unmatched_bureau():
    async def fn(name: str, dob: str, address: str) -> CreditBureauResult:
        return CreditBureauResult(matched=False)

    return fn


def _erroring_bureau(error: str = "timeout"):
    async def fn(name: str, dob: str, address: str) -> CreditBureauResult:
        return CreditBureauResult(matched=None, error=error)

    return fn


def _should_not_be_called():
    async def fn(*args, **kwargs):  # pragma: no cover
        raise AssertionError("collector should not have been called")

    return fn


def _matched_abr():
    async def fn(abn: str) -> AbrResult:
        return AbrResult(
            found=True,
            entity_name="Example Pty Ltd",
            abn_status="Active",
            entity_type="Australian Private Company",
            gst_registered=True,
            address_state="NSW",
        )

    return fn


async def test_incomplete_identity_skips_bureau_and_character_is_unavailable_no_score() -> None:
    await seed()
    async with AsyncSessionLocal() as db:
        report = await assess_application(
            db,
            {"applicant": {"name": "Daniel Osei"}},  # missing dob and address
            get_credit_report=_should_not_be_called(),
        )

    assert report.five_cs.character.value is None
    assert report.five_cs.character.source == "unavailable"
    assert report.five_cs.character.confidence == "low"
    assert "score" not in report.five_cs.character.model_dump_json()

    bureau_source = next(s for s in report.data_sources if s.source == "mock_bureau")
    assert bureau_source.called is False


async def test_no_abn_skips_abr_lookup() -> None:
    await seed()
    async with AsyncSessionLocal() as db:
        report = await assess_application(db, {"applicant": {"name": "x"}})

    abr_source = next(s for s in report.data_sources if s.source == "abr")
    assert abr_source.called is False
    assert abr_source.reason == "no ABN provided"


async def test_bureau_no_match_yields_unavailable_not_zero_score() -> None:
    await seed()
    async with AsyncSessionLocal() as db:
        report = await assess_application(
            db,
            {
                "applicant": {
                    "name": "Nobody Real",
                    "dob": "2000-01-01",
                    "address": "nowhere",
                }
            },
            get_credit_report=_unmatched_bureau(),
        )

    assert report.five_cs.character.value is None
    assert report.five_cs.character.source == "unavailable"
    bureau_source = next(s for s in report.data_sources if s.source == "mock_bureau")
    assert bureau_source.called is True
    assert bureau_source.matched is False


async def test_bureau_error_degrades_gracefully_rest_of_report_assembles() -> None:
    await seed()
    async with AsyncSessionLocal() as db:
        report = await assess_application(
            db,
            {
                "applicant": {
                    "name": "Daniel Osei",
                    "dob": "1990-07-22",
                    "address": "45 Banksia Ave",
                    "employment": {"income": 90000, "income_frequency": "Annually"},
                },
                "loan": {"amount": 20000, "term_months": 60},
            },
            get_credit_report=_erroring_bureau("timeout"),
        )

    assert report.five_cs.character.source == "unavailable"
    assert report.five_cs.character.value is None
    # The rest of the report still assembles — Capacity doesn't depend on the bureau.
    assert report.five_cs.capacity.source == "calculated"
    assert report.five_cs.capacity.value is not None

    bureau_source = next(s for s in report.data_sources if s.source == "mock_bureau")
    assert bureau_source.reason == "timeout"


async def test_complete_application_with_match_produces_full_report() -> None:
    await seed()
    async with AsyncSessionLocal() as db:
        report = await assess_application(
            db,
            {
                "applicant": {
                    "name": "Daniel Osei",
                    "dob": "1990-07-22",
                    "address": "45 Banksia Avenue, Marrickville NSW 2204",
                    "employment": {
                        "status": "Full-time",
                        "income": 95000,
                        "income_frequency": "Annually",
                    },
                    "monthly_expenses": 2100,
                },
                "loan": {
                    "amount": 40000,
                    "purpose": "Car purchase",
                    "term_months": 60,
                    "product_type": "car",
                },
                "collateral": {
                    "asset_type": "Vehicle",
                    "estimated_value": 42000,
                    "deposit_amount": 5000,
                },
            },
            get_credit_report=_matched_bureau(),
        )

    assert report.five_cs.character.source == "bureau-verified"
    assert report.five_cs.character.confidence == "high"
    assert report.five_cs.character.value["score"] == 742
    assert report.completeness.missing_fields == []
    assert report.completeness.score == 1.0


async def test_business_application_with_abn_shows_abr_verified_conditions() -> None:
    await seed()
    async with AsyncSessionLocal() as db:
        report = await assess_application(
            db,
            {
                "business": {"abn": "51824753556", "entity_name": "Example Pty Ltd"},
                "loan": {"purpose": "Working capital", "product_type": "business"},
            },
            lookup_abn=_matched_abr(),
        )

    assert report.five_cs.conditions.source == "abn-verified"
    assert report.five_cs.conditions.confidence == "high"
    assert report.five_cs.conditions.value["abn_status"] == "Active"
    assert report.five_cs.conditions.value["entity_type"] == "Australian Private Company"

    abr_source = next(s for s in report.data_sources if s.source == "abr")
    assert abr_source.called is True
    assert abr_source.matched is True


async def test_business_application_capacity_uses_declared_net_profit() -> None:
    await seed()
    async with AsyncSessionLocal() as db:
        report = await assess_application(
            db,
            {
                "loan": {"product_type": "business"},
                "business": {
                    "abn": "51824753556",
                    "entity_name": "Example Pty Ltd",
                    "net_profit": 120000,
                    "annual_turnover": 500000,
                    "industry": "Hospitality",
                },
            },
            lookup_abn=_matched_abr(),
        )

    assert report.five_cs.capacity.source == "calculated"
    assert report.five_cs.capacity.value["monthly_income"] == 10000.0
    assert report.five_cs.capacity.notes is not None
    assert "net profit" in report.five_cs.capacity.notes.lower()

    assert report.five_cs.conditions.source == "abn-verified"
    assert report.five_cs.conditions.value["industry"] == "Hospitality"

    missing_keys = {m.field for m in report.completeness.missing_fields}
    assert "business.net_profit" not in missing_keys
    assert "business.annual_turnover" not in missing_keys
    assert "business.industry" not in missing_keys


async def test_car_application_with_balloon_payment_affects_capacity_and_collateral() -> None:
    await seed()
    async with AsyncSessionLocal() as db:
        report = await assess_application(
            db,
            {
                "applicant": {"employment": {"income": 60000, "income_frequency": "Annually"}},
                "loan": {
                    "product_type": "car",
                    "amount": 40000,
                    "term_months": 60,
                    "balloon_payment": 10000,
                },
                "collateral": {"asset_type": "Vehicle", "estimated_value": 40000},
            },
        )

    assert report.five_cs.capacity.value["new_loan_estimated_monthly_repayment"] == 608.29
    assert "balloon" in report.five_cs.capacity.notes.lower()
    assert report.five_cs.collateral.source == "applicant-declared"
    assert report.five_cs.collateral.value["asset_type"] == "Vehicle"

    missing_keys = {m.field for m in report.completeness.missing_fields}
    assert "collateral.asset_type" not in missing_keys
    assert "collateral.estimated_value" not in missing_keys


async def test_report_always_returns_successfully_for_empty_application() -> None:
    await seed()
    async with AsyncSessionLocal() as db:
        report = await assess_application(db, {})

    assert report.five_cs.character.source == "unavailable"
    assert report.five_cs.capacity.source == "unavailable"
    assert report.five_cs.capital.source == "unavailable"
    assert report.five_cs.collateral.source == "unavailable"
    assert report.five_cs.conditions.source == "unavailable"
    assert report.completeness.score < 1.0
