from datetime import date, timedelta

SAMPLE_STATEMENT = (
    [{"direction": "credit", "category": "salary", "amount": 3200} for _ in range(3)]
    + [
        {"direction": "debit", "category": "exp_food_groceries", "amount": 650},
        {"direction": "debit", "category": "exp_rent_board", "amount": 1400},
        {"direction": "debit", "category": "exp_insurance", "amount": 180},
    ]
)

_APPLICANT = {
    "full_name": "Jane Citizen", "date_of_birth": "1990-05-14", "credit_check_consent": True,
    "employment_status": "full_time", "employer_name": "Bunnings Warehouse",
    "residency_status": "citizen", "months_in_current_role": 36, "employer_industry": "retail_trade",
    "dependants": 0, "marital_status": "single", "savings_balance": 25000,
    "other_loan_repayments_monthly": 0, "credit_card_limit_total": 5000,
    "exp_food_groceries": 600, "exp_rent_board": 1400, "exp_insurance": 180,
    "net_income_frequency": "fortnightly",
}


def _take_home_fortnightly(gross: int) -> int:
    brackets = [(18200, 0.0), (45000, 0.16), (135000, 0.30), (190000, 0.37), (float("inf"), 0.45)]
    tax, lower = 0.0, 0
    for upper, rate in brackets:
        if gross > lower:
            tax += (min(gross, upper) - lower) * rate
        lower = upper
    return round((gross - tax - gross * 0.02) / 26)


def _income(gross: int) -> dict:
    return {"gross_annual_income": gross, "net_income_amount": _take_home_fortnightly(gross)}

PRESETS = [
    {
        "id": "personal_strong", "label": "Strong personal loan applicant",
        "description": "Solid income, clean credit file. Expect approve recommended.",
        "product_code": "PL-STD-001", "bureau_scenario": "prime", "use_sample_statement": True,
        "filled": {**_APPLICANT, **_income(95000),
                   "loan_amount": 20000, "loan_term_months": 60, "loan_purpose": "debt_consolidation"},
    },
    {
        "id": "personal_stretched", "label": "Overstretched borrower",
        "description": "Large loan on a modest income. Expect decline on serviceability.",
        "product_code": "PL-STD-001", "bureau_scenario": "prime", "use_sample_statement": False,
        "filled": {**_APPLICANT, **_income(48000),
                   "exp_food_groceries": 900, "exp_rent_board": 1800, "exp_insurance": 250,
                   "other_loan_repayments_monthly": 400,
                   "loan_amount": 45000, "loan_term_months": 36, "loan_purpose": "home_improvement"},
    },
    {
        "id": "personal_hidden_debt", "label": "Undisclosed debts",
        "description": "Declares no loans but the credit file shows a personal loan and BNPL.",
        "product_code": "PL-STD-001", "bureau_scenario": "undisclosed_debt", "use_sample_statement": True,
        "filled": {**_APPLICANT, **_income(90000),
                   "loan_amount": 15000, "loan_term_months": 48, "loan_purpose": "medical"},
    },
    {
        "id": "personal_unpaid_default", "label": "Unpaid default on file",
        "description": "Good income, but a default and 90-day arrears on the credit file.",
        "product_code": "PL-STD-001", "bureau_scenario": "unpaid_default", "use_sample_statement": True,
        "filled": {**_APPLICANT, **_income(90000),
                   "loan_amount": 15000, "loan_term_months": 48, "loan_purpose": "education"},
    },
    {
        "id": "vehicle_minor_arrears", "label": "Vehicle loan, minor past arrears",
        "description": "Two old late payments. Not enough on its own to flag.",
        "product_code": "VL-NEW-020", "bureau_scenario": "minor_arrears", "use_sample_statement": True,
        "filled": {**_APPLICANT, **_income(85000),
                   "loan_amount": 32000, "loan_term_months": 60, "loan_purpose": "purchase_vehicle",
                   "vehicle_purchase_price": 35000, "trade_in_or_deposit": 3000,
                   "vehicle_year": 2025, "wants_balloon": False},
    },
    {
        "id": "home_good_deposit", "label": "Home loan, 25% deposit",
        "description": "Comfortable deposit and serviceability.",
        "product_code": "HL-VAR-010", "bureau_scenario": "prime", "use_sample_statement": True,
        "filled": {**_APPLICANT, **_income(190000),
                   "savings_balance": 160000, "loan_amount": 450000, "loan_term_months": 360,
                   "loan_purpose": "purchase_property", "property_price": 600000,
                   "deposit_amount": 150000, "deposit_source": "genuine_savings",
                   "repayment_type": "principal_and_interest"},
    },
    {
        "id": "home_lmi_deposit", "label": "Home loan, 13% deposit",
        "description": "Meets the minimum but under 20%. Expect an LMI flag.",
        "product_code": "HL-VAR-010", "bureau_scenario": "prime", "use_sample_statement": True,
        "filled": {**_APPLICANT, **_income(210000),
                   "savings_balance": 90000, "loan_amount": 520000, "loan_term_months": 360,
                   "loan_purpose": "purchase_property", "property_price": 600000,
                   "deposit_amount": 80000, "deposit_source": "genuine_savings",
                   "repayment_type": "principal_and_interest"},
    },
    {
        "id": "home_low_deposit", "label": "Home loan, 3% deposit (gift)",
        "description": "Deposit below the product minimum. Expect decline.",
        "product_code": "HL-VAR-010", "bureau_scenario": "prime", "use_sample_statement": True,
        "filled": {**_APPLICANT, **_income(240000),
                   "savings_balance": 32000, "loan_amount": 580000, "loan_term_months": 360,
                   "loan_purpose": "purchase_property", "property_price": 600000,
                   "deposit_amount": 20000, "deposit_source": "gift", "repayment_type": "principal_and_interest"},
    },
    {
        "id": "no_credit_consent", "label": "No credit-check consent",
        "description": "Applicant declined the credit check. Character metrics stay unavailable.",
        "product_code": "PL-STD-001", "bureau_scenario": "prime", "use_sample_statement": True,
        "filled": {**_APPLICANT, "credit_check_consent": False, **_income(95000), "loan_amount": 20000, "loan_term_months": 60,
                   "loan_purpose": "debt_consolidation"},
    },
    # ---- Conditions: one applicant per rule --------------------------------------------------------------
    {
        "id": "cond_business_purpose", "label": "Personal loan for business use",
        "description": "Consumer credit cannot be used for business. Expect decline: excluded purpose.",
        "product_code": "PL-STD-001", "bureau_scenario": "prime", "use_sample_statement": True,
        "filled": {**_APPLICANT, **_income(95000),
                   "loan_amount": 20000, "loan_term_months": 60, "loan_purpose": "business_use"},
    },
    {
        "id": "cond_above_product_max", "label": "Asks for more than the product allows",
        "description": "$60,000 on a product capped at $50,000. Expect decline: outside product limits.",
        "product_code": "PL-STD-001", "bureau_scenario": "prime", "use_sample_statement": True,
        "filled": {**_APPLICANT, **_income(140000),
                   "loan_amount": 60000, "loan_term_months": 60, "loan_purpose": "debt_consolidation"},
    },
    {
        "id": "cond_visa_short", "label": "Temporary visa ends before the loan does",
        "description": "Visa expires in about 18 months but the loan runs 60. Expect an underwriter flag.",
        "product_code": "PL-STD-001", "bureau_scenario": "prime", "use_sample_statement": True,
        "filled": {**_APPLICANT, **_income(95000),
                   "residency_status": "temporary_visa", "visa_subclass": "482",
                   "visa_expiry_date": (date.today() + timedelta(days=548)).isoformat(),
                   "loan_amount": 20000, "loan_term_months": 60, "loan_purpose": "home_improvement"},
    },
    {
        "id": "cond_casual_new_job", "label": "Casual worker, 4 months in the job",
        "description": "Casual staff need 12 months in the role under the placeholder policy. Expect a flag.",
        "product_code": "PL-STD-001", "bureau_scenario": "prime", "use_sample_statement": True,
        "filled": {**_APPLICANT, "employment_status": "casual", "months_in_current_role": 4, "on_probation": True,
                   **_income(70000),
                   "loan_amount": 15000, "loan_term_months": 48, "loan_purpose": "travel"},
    },
    {
        "id": "cond_older_borrower", "label": "Older borrower on a 25 year home loan",
        "description": "Will be about 93 when the loan ends, over the policy age. Expect a flag and an exit strategy condition.",
        "product_code": "HL-VAR-010", "bureau_scenario": "prime", "use_sample_statement": True,
        "filled": {**_APPLICANT, "date_of_birth": "1958-03-02", **_income(160000),
                   "savings_balance": 170000, "loan_amount": 350000, "loan_term_months": 300,
                   "loan_purpose": "purchase_property", "property_price": 500000, "deposit_amount": 150000,
                   "deposit_source": "genuine_savings", "repayment_type": "principal_and_interest"},
    },
    {
        "id": "cond_old_vehicle", "label": "2010 used car on a 5 year loan",
        "description": "The car would be 21 years old when the loan ends; the limit is 12. Expect decline.",
        "product_code": "VL-USED-021", "bureau_scenario": "prime", "use_sample_statement": True,
        "filled": {**_APPLICANT, **_income(95000),
                   "loan_amount": 10000, "loan_term_months": 60, "loan_purpose": "purchase_vehicle",
                   "vehicle_purchase_price": 12000, "trade_in_or_deposit": 2000, "vehicle_year": 2010, "wants_balloon": False},
    },
    {
        "id": "cond_big_balloon", "label": "Vehicle loan with a 40% balloon",
        "description": "Balloon above the 30% cap. Expect a flag and a suitability condition.",
        "product_code": "VL-NEW-020", "bureau_scenario": "prime", "use_sample_statement": True,
        "filled": {**_APPLICANT, **_income(95000),
                   "loan_amount": 40000, "loan_term_months": 60, "loan_purpose": "purchase_vehicle",
                   "vehicle_purchase_price": 45000, "trade_in_or_deposit": 5000, "vehicle_year": 2025,
                   "wants_balloon": True, "balloon_percentage": 40},
    },
    {
        "id": "cond_high_risk_industry", "label": "Self-employed builder, 1 year trading",
        "description": "Two flags: under 2 years trading, and a higher-risk industry.",
        "product_code": "PL-STD-001", "bureau_scenario": "prime", "use_sample_statement": True,
        "filled": {**_APPLICANT, "employment_status": "self_employed", "abn_years_trading": 1, "months_in_current_role": 12,
                   "employer_industry": "construction", **_income(95000),
                   "loan_amount": 20000, "loan_term_months": 60, "loan_purpose": "home_improvement"},
    },
]
