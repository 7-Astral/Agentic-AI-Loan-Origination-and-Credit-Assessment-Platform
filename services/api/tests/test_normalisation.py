from decimal import Decimal

from agents.risk_assessment.normalise import normalise_application


def test_absent_fields_do_not_raise_and_yield_none() -> None:
    result = normalise_application({})
    assert result.applicant.name is None
    assert result.applicant.employment.income is None
    assert result.loan.amount is None
    assert result.existing_debt.loans == []
    assert result.business.abn is None
    assert result.collateral.estimated_value is None


def test_non_dict_input_does_not_raise() -> None:
    result = normalise_application(None)  # type: ignore[arg-type]
    assert result.applicant.name is None

    result = normalise_application("not an application")  # type: ignore[arg-type]
    assert result.applicant.name is None


def test_mixed_date_formats_parse() -> None:
    for raw, expected in [
        ("1990-07-22", "1990-07-22"),
        ("22/07/1990", "1990-07-22"),
        ("22-07-1990", "1990-07-22"),
        ("22 July 1990", "1990-07-22"),
        ("July 22, 1990", "1990-07-22"),
    ]:
        result = normalise_application({"applicant": {"dob": raw}})
        assert result.applicant.dob is not None
        assert result.applicant.dob.isoformat() == expected


def test_unparseable_date_yields_none_not_raise() -> None:
    result = normalise_application({"applicant": {"dob": "not a date"}})
    assert result.applicant.dob is None


def test_currency_strings_parse_to_decimal() -> None:
    for raw, expected in [
        ("$85,000", Decimal("85000")),
        ("85k", Decimal("85000")),
        ("85000", Decimal("85000")),
        (85000, Decimal("85000")),
        (85000.5, Decimal("85000.5")),
    ]:
        result = normalise_application({"applicant": {"employment": {"income": raw}}})
        assert result.applicant.employment.income == expected


def test_unparseable_currency_yields_none_not_raise() -> None:
    result = normalise_application({"loan": {"amount": "not a number"}})
    assert result.loan.amount is None


def test_whitespace_is_trimmed() -> None:
    result = normalise_application({"applicant": {"name": "  Daniel Osei  "}})
    assert result.applicant.name == "Daniel Osei"


def test_blank_string_normalises_to_none() -> None:
    result = normalise_application({"applicant": {"name": "   "}})
    assert result.applicant.name is None


def test_existing_debt_lists_normalise() -> None:
    result = normalise_application(
        {
            "existing_debt": {
                "loans": [{"type": "personal", "balance": "5,000", "monthly_repayment": "150"}],
                "bnpl_accounts": [{"provider": "Afterpay", "limit": 2000, "balance": 500}],
                "credit_cards": [{"limit": "5000", "balance": "1,200.50"}],
            }
        }
    )
    assert result.existing_debt.loans[0].balance == Decimal("5000")
    assert result.existing_debt.bnpl_accounts[0].balance == Decimal("500")
    assert result.existing_debt.credit_cards[0].balance == Decimal("1200.50")


def test_malformed_list_items_are_skipped_not_raised() -> None:
    result = normalise_application({"existing_debt": {"loans": ["not a dict", 123, None]}})
    assert result.existing_debt.loans == []


def test_full_application_normalises() -> None:
    result = normalise_application(
        {
            "applicant": {
                "name": "Daniel Osei",
                "dob": "22/07/1990",
                "address": "45 Banksia Avenue, Marrickville NSW 2204",
                "employment": {
                    "status": "Full-time",
                    "employer": "Acme Pty Ltd",
                    "years_in_role": "3",
                    "income": "$95,000",
                    "income_frequency": "Annually",
                },
                "monthly_expenses": "2,100",
            },
            "loan": {"amount": "40,000", "purpose": "Car purchase", "term_months": "60"},
            "business": {"abn": "51824753556", "entity_name": "Acme Pty Ltd"},
            "collateral": {
                "asset_type": "Vehicle",
                "estimated_value": "42000",
                "deposit_amount": "5000",
            },
        }
    )
    assert result.applicant.name == "Daniel Osei"
    assert result.applicant.dob is not None and result.applicant.dob.isoformat() == "1990-07-22"
    assert result.applicant.employment.income == Decimal("95000")
    assert result.loan.amount == Decimal("40000")
    assert result.loan.term_months == 60
    assert result.business.abn == "51824753556"
    assert result.collateral.estimated_value == Decimal("42000")


def test_loan_boolean_fields_coerce_from_native_and_string_json() -> None:
    result = normalise_application({"loan": {"interest_only": True, "balloon_payment": "5000"}})
    assert result.loan.interest_only is True
    assert result.loan.balloon_payment == Decimal("5000")

    result = normalise_application({"loan": {"interest_only": "true"}})
    assert result.loan.interest_only is True

    result = normalise_application({"loan": {"interest_only": "false"}})
    assert result.loan.interest_only is False

    result = normalise_application({"loan": {}})
    assert result.loan.interest_only is None


def test_business_financial_fields_normalise() -> None:
    result = normalise_application(
        {
            "business": {
                "abn": "51824753556",
                "industry": "Hospitality",
                "years_trading": "4.5",
                "annual_turnover": "$500,000",
                "net_profit": "120,000",
                "employee_count": "12",
            }
        }
    )
    assert result.business.industry == "Hospitality"
    assert result.business.years_trading == 4.5
    assert result.business.annual_turnover == Decimal("500000")
    assert result.business.net_profit == Decimal("120000")
    assert result.business.employee_count == 12
