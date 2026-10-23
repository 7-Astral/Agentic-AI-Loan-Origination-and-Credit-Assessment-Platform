from datetime import date

from app.agents.assessment.business.metrics.conditions import entity_structure_review
from app.agents.document.business_cashflow import summarise_business_cashflow
from app.agents.document.reconcile import BUSINESS_RECONCILIATION_RULES, reconcile
from app.agents.document.requirements import applies, order_key
from app.agents.document.schemas import EXTRACTION_SCHEMAS

TODAY = date(2026, 10, 11)

FILLED = {
    "full_name": "Jane Citizen",
    "business_name": "Harbour Bakery Pty Ltd",
    "abn_or_acn": "51 824 753 556",
    "entity_structure": "company",
    "years_trading": 4,
    "annual_turnover": 820000,
    "net_profit_before_tax": 95000,
    "interest_expense_annual": 12000,
    "depreciation_amortisation_annual": 18000,
    "current_assets": 140000,
    "current_liabilities": 90000,
    "total_business_liabilities": 260000,
    "total_business_equity": 180000,
    "prior_year_annual_turnover": 760000,
    "prior_year_net_profit_before_tax": 81000,
    "existing_business_debt_repayments": 3000,
    "ato_obligations_current": True,
    "loan_amount": 150000,
}


def _by_slot(results):
    return {r["slot_id"]: r for r in results}


def test_every_business_rule_reads_a_field_the_extractor_returns():
    derived = {"annualised_sales_receipts", "monthly_loan_repayments"}
    for code, rules in BUSINESS_RECONCILIATION_RULES.items():
        fields = set(EXTRACTION_SCHEMAS[code]) | derived
        for rule in rules:
            for name in [rule["extracted_field"], *rule.get("alt_extracted_fields", [])]:
                assert name in fields, f"{code}: {name}"


def test_registration_matches_name_abn_and_trading_period():
    extracted = {
        "business_name": "HARBOUR BAKERY PTY LTD", "abn": "51824753556",
        "abn_active_from": "2021-07-01",
    }
    results = _by_slot(reconcile("business_registration", extracted, FILLED, loan_type="business", today=TODAY))
    assert results["business_name"]["status"] == "match"
    assert results["abn_or_acn"]["status"] == "match"
    assert results["years_trading"]["status"] == "match"


def test_registration_flags_overstated_trading_history():
    extracted = {"business_name": "Harbour Bakery Pty Ltd", "abn": "51824753556", "abn_active_from": "2025-01-15"}
    results = _by_slot(reconcile("business_registration", extracted, FILLED, loan_type="business", today=TODAY))
    assert results["years_trading"]["status"] == "mismatch"


def test_acn_matches_when_applicant_gave_acn():
    filled = {**FILLED, "abn_or_acn": "824 753 556"}
    extracted = {"business_name": "Harbour Bakery Pty Ltd", "abn": "51824753556", "acn": "824753556"}
    results = _by_slot(reconcile("business_registration", extracted, filled, loan_type="business", today=TODAY))
    assert results["abn_or_acn"]["status"] == "match"
    assert results["abn_or_acn"]["extracted_value"] == "824753556"


def test_financial_statements_check_every_figure_the_assessment_uses():
    extracted = {
        "entity_name": "Harbour Bakery Pty Ltd", "revenue": 821500, "net_profit_before_tax": 95000,
        "interest_expense": 12000, "depreciation_amortisation": 18000, "current_assets": 140000,
        "current_liabilities": 90000, "total_liabilities": 260000, "total_equity": 180000,
        "prior_year_revenue": 760000, "prior_year_net_profit_before_tax": 60000,
    }
    results = _by_slot(reconcile("financial_statements", extracted, FILLED, loan_type="business"))
    assert results["annual_turnover"]["status"] == "match"
    assert results["prior_year_net_profit_before_tax"]["status"] == "mismatch"
    assert "two_years_prior_annual_turnover" not in results
    assert all(results[s]["status"] == "match" for s in (
        "net_profit_before_tax", "interest_expense_annual", "depreciation_amortisation_annual",
        "current_assets", "current_liabilities", "total_business_liabilities", "total_business_equity",
    ))


def test_financial_statements_report_missing_required_figure():
    extracted = {"entity_name": "Harbour Bakery Pty Ltd", "revenue": 820000}
    results = _by_slot(reconcile("financial_statements", extracted, FILLED, loan_type="business"))
    assert results["interest_expense_annual"]["status"] == "missing"


def test_ato_statement_contradicts_up_to_date_claim():
    extracted = {"abn": "51824753556", "outstanding_amount": 14200, "overdue_amount": 9000, "overdue_lodgments": "BAS Q4 2026"}
    results = reconcile("ato_position", extracted, FILLED, loan_type="business")
    statuses = [r["status"] for r in results if r["slot_id"] == "ato_obligations_current"]
    assert statuses == ["mismatch", "mismatch"]


def test_ato_statement_clear_matches():
    extracted = {"outstanding_amount": 0, "overdue_amount": 0, "overdue_lodgments": "None"}
    results = reconcile("ato_position", extracted, FILLED, loan_type="business")
    assert {r["status"] for r in results if r["slot_id"] == "ato_obligations_current"} == {"match"}


def test_business_bank_statement_accepts_business_or_personal_name():
    business = reconcile("bank_statements", {"account_holder_name": "Harbour Bakery Pty Ltd"}, FILLED, loan_type="business")
    personal = reconcile("bank_statements", {"account_holder_name": "Jane Citizen"}, FILLED, loan_type="business")
    assert business[0]["status"] == personal[0]["status"] == "match"


def test_retail_rules_unchanged():
    results = reconcile("bank_statements", {"account_holder_name": "Harbour Bakery Pty Ltd"}, FILLED)
    assert [r["slot_id"] for r in results] == ["full_name"]
    assert results[0]["status"] == "mismatch"


def test_cashflow_summary_annualises_sales_and_repayments():
    fields = {
        "statement_period_start": "2026-07-01", "statement_period_end": "2026-09-30",
        "transactions": [
            {"date": "2026-07-03", "amount": 70000, "direction": "credit", "category": "sales_revenue"},
            {"date": "2026-08-03", "amount": 66000, "direction": "credit", "category": "sales_revenue"},
            {"date": "2026-09-03", "amount": 69000, "direction": "credit", "category": "sales_revenue"},
            {"date": "2026-08-10", "amount": 50000, "direction": "credit", "category": "loan_proceeds"},
            {"date": "2026-07-15", "amount": 3000, "direction": "debit", "category": "loan_repayment"},
            {"date": "2026-08-15", "amount": 3000, "direction": "debit", "category": "loan_repayment"},
            {"date": "2026-09-15", "amount": 3000, "direction": "debit", "category": "loan_repayment"},
            {"date": "2026-09-20", "amount": 15, "direction": "debit", "category": "dishonour"},
        ],
    }
    summary = summarise_business_cashflow(fields)
    assert summary["cashflow_period_days"] == 92
    assert 800000 < summary["annualised_sales_receipts"] < 830000
    assert 2900 < summary["monthly_loan_repayments"] < 3000
    assert summary["cashflow_dishonour_count"] == 1

    results = _by_slot(reconcile("bank_statements", {**fields, **summary, "account_holder_name": "Harbour Bakery Pty Ltd"},
                                 FILLED, loan_type="business"))
    assert results["annual_turnover"]["status"] == "match"
    assert results["existing_business_debt_repayments"]["status"] == "match"


def test_cashflow_summary_needs_categories():
    assert summarise_business_cashflow({"transactions": [{"date": "2026-07-01", "amount": 5, "direction": "credit"}]}) == {}


def test_contract_of_sale_must_cover_loan_amount():
    results = _by_slot(reconcile(
        "contract_of_sale", {"buyer_name": "Harbour Bakery Pty Ltd", "purchase_price": 120000}, FILLED, loan_type="business",
    ))
    assert results["loan_amount"]["status"] == "mismatch"


def test_entity_documents_only_requested_for_entities_that_have_them():
    assert applies("entity_documents", {"entity_structure": "trust"})
    assert not applies("entity_documents", {"entity_structure": "sole_trader"})
    assert applies("entity_documents", {})
    assert applies("financial_statements", {"entity_structure": "sole_trader"})


def test_uploaded_entity_document_satisfies_review():
    filled = {"entity_structure": "trust"}
    assert entity_structure_review(filled).value == "needs_review"
    assert entity_structure_review(filled, {"entity_documents"}).value == "reviewed"


def test_business_documents_are_asked_in_a_natural_order():
    codes = ["tax_return", "ato_position", "bank_statements", "primary_photo_id", "entity_documents",
             "financial_statements", "business_registration"]
    assert sorted(codes, key=order_key) == [
        "primary_photo_id", "business_registration", "entity_documents", "financial_statements",
        "tax_return", "ato_position", "bank_statements",
    ]
