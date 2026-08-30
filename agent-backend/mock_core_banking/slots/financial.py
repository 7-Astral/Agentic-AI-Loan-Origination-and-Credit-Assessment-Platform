
from .core import slot

RENTS_OR_BOARDS = "living_arrangement in ('renting', 'boarding')"
HAS_MORTGAGE = "living_arrangement == 'own_with_mortgage'"

# Phase 4a — assets
ASSETS = [
    slot(
        "savings_balance", "Savings and term deposits", 4, "currency",
        "Total across accounts; approximate is fine",
        validation={"min": 0},
        verification="bank_statements",
        regulatory_basis="Financial situation inquiry",
        group="assets",
    ),
    slot(
        "owns_property", "Owns any property", 4, "boolean",
        "Any property owned, including the one they live in",
        group="assets",
    ),
    slot(
        "property_equity_value", "Estimated property value", 4, "currency",
        "Their estimate of market value across properties owned",
        required_when="owns_property == True",
        validation={"min": 0},
        group="assets",
    ),
    slot(
        "vehicles_value", "Vehicles owned", 4, "currency",
        "Approximate value; skip if none",
        required=False,
        validation={"min": 0},
        group="assets",
    ),
    slot(
        "investments_value", "Shares and managed funds", 4, "currency",
        "Approximate value; skip if none",
        required=False,
        validation={"min": 0},
        group="assets",
    ),
]

# Phase 4b — liabilities
LIABILITIES = [
    slot(
        "mortgage_balance", "Mortgage balance outstanding", 4, "currency",
        "Only when they own with a mortgage",
        required_when=HAS_MORTGAGE,
        validation={"min": 0},
        verification="loan_statement",
        group="liabilities",
    ),
    slot(
        "mortgage_repayment_monthly", "Mortgage repayment per month", 4, "currency",
        "Normalise to monthly whatever frequency they give",
        required_when=HAS_MORTGAGE,
        validation={"min": 0},
        group="liabilities",
    ),
    slot(
        "credit_card_limit_total", "Total credit card limits", 4, "currency",
        "The limit, not the balance — assessed on the limit regardless of use",
        validation={"min": 0},
        regulatory_basis="Serviceability assessment",
        group="liabilities",
    ),
    slot(
        "credit_card_balance_total", "Total credit card balances", 4, "currency",
        "Currently owing across all cards",
        required_when="credit_card_limit_total > 0",
        validation={"min": 0},
        group="liabilities",
    ),
    slot(
        "other_loan_repayments_monthly", "Other loan repayments per month", 4, "currency",
        "Personal loans, car loans, leases, hire purchase, ATO payment plans",
        validation={"min": 0},
        regulatory_basis="Serviceability assessment",
        group="liabilities",
    ),
    slot(
        "has_hecs_help", "Has HECS or HELP debt", 4, "boolean",
        "Contingent liability; affects net income",
        group="liabilities",
    ),
    slot(
        "hecs_help_balance", "HECS or HELP balance", 4, "currency",
        "Approximate outstanding balance",
        required_when="has_hecs_help == True",
        validation={"min": 0},
        group="liabilities",
    ),
    slot(
        "contingent_liabilities", "Guarantees or other commitments", 4, "text",
        "Guarantees given for others, rental bonds, anything not yet listed",
        required=False,
        group="liabilities",
    ),
]

# Phase 4c — living expenses.
# Two rules attach to every one of these: enter 0 for anything not paid,
# and where an expense is shared, include only their own contribution,
# counting each expense exactly once.
_EXPENSE_RULE = "Monthly, own contribution only, 0 if not applicable"

EXPENSES = [
    slot("exp_food_groceries", "Food and groceries", 4, "currency",
         _EXPENSE_RULE, validation={"min": 0}, group="expenses",
         regulatory_basis="Expense benchmarking"),
    slot("exp_clothing_personal_care", "Clothing and personal care", 4, "currency",
         _EXPENSE_RULE, validation={"min": 0}, group="expenses"),
    slot("exp_recreation_holidays", "Recreation and holidays", 4, "currency",
         _EXPENSE_RULE, validation={"min": 0}, group="expenses"),
    slot("exp_education_childcare", "Education, childcare and dependants", 4, "currency",
         _EXPENSE_RULE, validation={"min": 0}, group="expenses"),
    slot("exp_insurance", "Insurance", 4, "currency",
         _EXPENSE_RULE, validation={"min": 0}, group="expenses"),
    slot("exp_medical_health", "Medical and health", 4, "currency",
         _EXPENSE_RULE, validation={"min": 0}, group="expenses"),
    slot("exp_rent_board", "Rent or board", 4, "currency",
         "Only when renting or boarding; their share",
         required_when=RENTS_OR_BOARDS, validation={"min": 0}, group="expenses"),
    slot("exp_other_housing", "Other housing costs", 4, "currency",
         "Rates, strata, utilities, maintenance — excluding mortgage",
         validation={"min": 0}, group="expenses"),
    slot("exp_phone_internet_media", "Phone, internet and media", 4, "currency",
         _EXPENSE_RULE, validation={"min": 0}, group="expenses"),
    slot("exp_vehicle_transport", "Vehicle and transport", 4, "currency",
         "Fuel, registration, servicing, public transport — not loan repayments",
         validation={"min": 0}, group="expenses"),
]

# Phase 6 — verification and consent
PHASE_6 = [
    slot(
        "credit_check_consent", "Consent to credit check", 6, "boolean",
        "Explicit consent before any bureau enquiry",
        regulatory_basis="Privacy Act consent",
        group="consent",
    ),
    slot(
        "privacy_acknowledged", "Privacy notice acknowledged", 6, "boolean",
        "Confirm they have seen how their information is handled",
        regulatory_basis="Privacy Act notification",
        group="consent",
    ),
    slot(
        "documents_available", "Documents they can provide", 6, "text",
        "What they already have to hand; the rest is requested later",
        required=False,
        group="consent",
    ),
]

# Phase 7 — confirmation
PHASE_7 = [
    slot(
        "summary_confirmed", "Summary confirmed by applicant", 7, "boolean",
        "Read the structured summary back and let them correct anything",
        regulatory_basis="Assessment accuracy",
        group="confirmation",
    ),
]

PHASE_4 = ASSETS + LIABILITIES + EXPENSES
FINANCIAL_SLOTS = PHASE_4 + PHASE_6 + PHASE_7