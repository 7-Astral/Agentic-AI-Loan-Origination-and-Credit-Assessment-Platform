from agents.risk_assessment.capacity import BENCHMARK_MONTHLY_EXPENSES, calculate_capacity
from agents.risk_assessment.normalise import normalise_application


def test_no_income_yields_unavailable_low_confidence() -> None:
    app = normalise_application({})
    result = calculate_capacity(app)
    assert result.value is None
    assert result.source == "unavailable"
    assert result.confidence == "low"


def test_worked_scenario_annual_income_with_debt_and_new_loan() -> None:
    app = normalise_application(
        {
            "applicant": {
                "employment": {"income": 90000, "income_frequency": "Annually"},
                "monthly_expenses": 2000,
            },
            "loan": {"amount": 20000, "term_months": 60},
            "existing_debt": {"loans": [{"monthly_repayment": 200}]},
        }
    )
    result = calculate_capacity(app)

    assert result.source == "calculated"
    assert result.confidence == "medium"
    assert result.value["monthly_income"] == 7500.0
    assert result.value["monthly_expenses"] == 2000.0
    assert result.value["existing_debt_monthly"] == 200.0
    assert result.value["new_loan_estimated_monthly_repayment"] == 405.53
    assert result.value["disposable_income_monthly"] == 4894.47
    assert result.value["servicing_ratio"] == 0.0807


def test_missing_expenses_falls_back_to_benchmark_and_notes_it() -> None:
    app = normalise_application(
        {"applicant": {"employment": {"income": 60000, "income_frequency": "Annually"}}}
    )
    result = calculate_capacity(app)

    assert result.value["monthly_expenses"] == float(BENCHMARK_MONTHLY_EXPENSES)
    assert result.notes is not None
    assert "benchmark" in result.notes.lower()


def test_weekly_income_frequency_converts_to_monthly() -> None:
    app = normalise_application(
        {"applicant": {"employment": {"income": 1200, "income_frequency": "Weekly"}}}
    )
    result = calculate_capacity(app)
    assert result.value["monthly_income"] == 5200.0


def test_missing_income_frequency_is_assumed_monthly_and_noted() -> None:
    app = normalise_application({"applicant": {"employment": {"income": 5000}}})
    result = calculate_capacity(app)
    assert result.value["monthly_income"] == 5000.0
    assert result.notes is not None
    assert "monthly" in result.notes.lower()


def test_undeclared_credit_card_and_bnpl_repayments_are_estimated() -> None:
    app = normalise_application(
        {
            "applicant": {"employment": {"income": 60000, "income_frequency": "Annually"}},
            "existing_debt": {
                "credit_cards": [{"balance": 1200}],
                "bnpl_accounts": [{"balance": 500}],
            },
        }
    )
    result = calculate_capacity(app)
    assert result.value["existing_debt_monthly"] == 61.0  # 3% of 1200 + 5% of 500
    assert "estimated" in result.notes.lower()


def test_missing_loan_term_prevents_new_loan_repayment_estimate() -> None:
    app = normalise_application(
        {
            "applicant": {"employment": {"income": 60000, "income_frequency": "Annually"}},
            "loan": {"amount": 20000},
        }
    )
    result = calculate_capacity(app)
    assert result.value["new_loan_estimated_monthly_repayment"] is None


def test_business_loan_uses_net_profit_not_personal_income() -> None:
    """Full replacement, not a blend — declared personal income is ignored for a business
    loan when net profit is available, to avoid double-counting owner earnings."""
    app = normalise_application(
        {
            "applicant": {"employment": {"income": 50000, "income_frequency": "Annually"}},
            "loan": {"product_type": "business"},
            "business": {"net_profit": 120000},
        }
    )
    result = calculate_capacity(app)

    assert result.source == "calculated"
    assert result.value["monthly_income"] == 10000.0
    assert result.value["disposable_income_monthly"] == 7500.0
    assert result.notes is not None
    assert "net profit" in result.notes.lower()
    assert "business debt" in result.notes.lower()


def test_business_loan_capacity_available_without_any_personal_income() -> None:
    """Guard restructure: a direct-API business application can declare net_profit with no
    personal income at all and must not short-circuit to unavailable."""
    app = normalise_application(
        {"loan": {"product_type": "business"}, "business": {"net_profit": 120000}}
    )
    result = calculate_capacity(app)
    assert result.source == "calculated"
    assert result.value["monthly_income"] == 10000.0


def test_net_profit_ignored_for_non_business_loan_type() -> None:
    app = normalise_application(
        {"loan": {"product_type": "personal"}, "business": {"net_profit": 120000}}
    )
    result = calculate_capacity(app)
    assert result.source == "unavailable"


def test_interest_only_investment_loan_repayment_is_interest_only() -> None:
    app = normalise_application(
        {
            "applicant": {"employment": {"income": 90000, "income_frequency": "Annually"}},
            "loan": {"amount": 300000, "term_months": 360, "interest_only": True},
        }
    )
    result = calculate_capacity(app)

    assert result.value["new_loan_estimated_monthly_repayment"] == 2000.0
    assert result.value["disposable_income_monthly"] == 3000.0
    assert result.value["servicing_ratio"] == 0.2667
    assert "interest-only" in result.notes.lower()


def test_balloon_payment_reduces_amortised_principal() -> None:
    app = normalise_application(
        {
            "applicant": {"employment": {"income": 60000, "income_frequency": "Annually"}},
            "loan": {"amount": 40000, "term_months": 60, "balloon_payment": 10000},
        }
    )
    result = calculate_capacity(app)

    assert result.value["new_loan_estimated_monthly_repayment"] == 608.29
    assert result.value["disposable_income_monthly"] == 1891.71
    assert result.value["servicing_ratio"] == 0.1217
    assert "balloon" in result.notes.lower()
