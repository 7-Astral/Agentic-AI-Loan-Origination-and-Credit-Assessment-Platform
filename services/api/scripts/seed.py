"""Idempotent seed data for local development.

NOTE: the interest rates, amount limits and term ranges below are synthetic development
placeholders chosen for demo purposes — they are not real product terms and must never be
treated as such.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.security import hash_password
from core.database import AsyncSessionLocal
from models.application import Application
from models.bank import Bank
from models.customer_profile import CustomerProfile
from models.enums import ApplicationStatus, BankStatus, LoanType, OfficerActionType, UserRole
from models.loan_product import LoanProduct
from models.officer_action import OfficerAction
from models.prompt_template import PromptTemplate
from models.question_template import QuestionTemplate
from models.required_field_template import RequiredFieldTemplate
from models.user import User

DEMO_BANK_SLUG = "demo-mutual"
AGENT_NAME = "loan_broker"

PRODUCTS: list[dict[str, Any]] = [
    {
        "name": "Standard Home Loan",
        "type": LoanType.home,
        "interest_rate": Decimal("6.14"),
        "min_amount": Decimal("100000"),
        "max_amount": Decimal("2000000"),
        "min_term_months": 120,
        "max_term_months": 360,
        "eligibility_rules": {"max_lvr": 0.80, "min_income": 50000},
    },
    {
        "name": "Investment Home Loan",
        "type": LoanType.investment,
        "interest_rate": Decimal("6.49"),
        "min_amount": Decimal("100000"),
        "max_amount": Decimal("2000000"),
        "min_term_months": 120,
        "max_term_months": 360,
        "eligibility_rules": {"max_lvr": 0.70, "min_income": 65000},
    },
    {
        "name": "Personal Loan",
        "type": LoanType.personal,
        "interest_rate": Decimal("11.95"),
        "min_amount": Decimal("5000"),
        "max_amount": Decimal("75000"),
        "min_term_months": 12,
        "max_term_months": 84,
        "eligibility_rules": {"min_income": 30000},
    },
    {
        "name": "Car Loan",
        "type": LoanType.car,
        "interest_rate": Decimal("8.25"),
        "min_amount": Decimal("10000"),
        "max_amount": Decimal("150000"),
        "min_term_months": 12,
        "max_term_months": 84,
        "eligibility_rules": {"min_income": 35000},
    },
    {
        "name": "Business Loan",
        "type": LoanType.business,
        "interest_rate": Decimal("9.80"),
        "min_amount": Decimal("20000"),
        "max_amount": Decimal("500000"),
        "min_term_months": 12,
        "max_term_months": 120,
        "eligibility_rules": {"min_income": 80000},
    },
]

BASELINE_QUESTIONS: list[dict[str, Any]] = [
    {
        "key": "employment_status",
        "prompt": "What's your current employment situation?",
        "type": "choice",
        "options": [
            "Full-time",
            "Part-time",
            "Casual",
            "Self-employed",
            "Contract",
            "Not currently employed",
        ],
        "required": True,
    },
    {
        "key": "annual_income",
        "prompt": "What's your annual income before tax?",
        "type": "currency",
        "required": True,
        "validation": {"min": 0, "max": 10000000},
        "help_text": "Include salary, bonuses and any regular additional income.",
    },
    {
        "key": "income_frequency",
        "prompt": "How often are you paid?",
        "type": "choice",
        "options": ["Weekly", "Fortnightly", "Monthly", "Annually"],
        "required": True,
    },
    {
        "key": "monthly_expenses",
        "prompt": "Roughly what are your total monthly living expenses?",
        "type": "currency",
        "required": True,
        "validation": {"min": 0, "max": 100000},
        "help_text": "Rent or board, groceries, utilities, transport, insurance, subscriptions.",
    },
    {
        "key": "existing_debts",
        "prompt": "Do you have any existing loans or credit cards?",
        "type": "boolean",
        "required": True,
    },
    {
        "key": "existing_debt_amount",
        "prompt": "What's the total amount owing across those?",
        "type": "currency",
        "required": False,
        "validation": {"min": 0, "max": 10000000},
        "help_text": "Only asked when the previous answer is yes.",
        "depends_on": {"key": "existing_debts", "equals": True},
    },
    {
        "key": "dependents",
        "prompt": "How many dependents do you have?",
        "type": "integer",
        "required": True,
        "validation": {"min": 0, "max": 20},
    },
    {
        "key": "loan_amount",
        "prompt": "How much would you like to borrow?",
        "type": "currency",
        "required": True,
        "validation": {"min": 1000, "max": 5000000},
    },
    {
        "key": "loan_term_years",
        "prompt": "Over how many years would you like to repay it?",
        "type": "integer",
        "required": True,
        "validation": {"min": 1, "max": 30},
    },
]

HOME_QUESTIONS: list[dict[str, Any]] = [
    {
        "key": "property_price",
        "prompt": "What's the approximate purchase price of the property?",
        "type": "currency",
        "required": True,
        "validation": {"min": 50000, "max": 10000000},
    },
    {
        "key": "deposit_amount",
        "prompt": "How much deposit do you have saved?",
        "type": "currency",
        "required": True,
        "validation": {"min": 0, "max": 10000000},
    },
    {
        "key": "first_home_buyer",
        "prompt": "Are you a first home buyer?",
        "type": "boolean",
        "required": True,
    },
    {
        "key": "property_type",
        "prompt": "What type of property is it?",
        "type": "choice",
        "options": ["House", "Apartment or unit", "Townhouse", "Land", "Other"],
        "required": True,
    },
    {
        "key": "property_state",
        "prompt": "Which state or territory is the property in?",
        "type": "choice",
        "options": ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"],
        "required": True,
    },
    {
        "key": "refinancing",
        "prompt": "Is this a refinance of an existing home loan, rather than a new purchase?",
        "type": "boolean",
        "required": True,
    },
    {
        "key": "existing_mortgage_balance",
        "prompt": "What's the current balance owing on the loan you're refinancing?",
        "type": "currency",
        "required": False,
        "validation": {"min": 0, "max": 10000000},
        "help_text": "Only asked when refinancing an existing home loan.",
        "depends_on": {"key": "refinancing", "equals": True},
    },
]

CAR_QUESTIONS: list[dict[str, Any]] = [
    {
        "key": "vehicle_price",
        "prompt": "What's the approximate price of the vehicle?",
        "type": "currency",
        "required": True,
        "validation": {"min": 1000, "max": 500000},
    },
    {
        "key": "vehicle_condition",
        "prompt": "Is it a new or used vehicle?",
        "type": "choice",
        "options": ["New", "Used"],
        "required": True,
    },
    {
        "key": "vehicle_year",
        "prompt": "What year is the vehicle?",
        "type": "integer",
        "required": False,
        "validation": {"min": 1950, "max": 2030},
    },
    {
        "key": "trade_in_value",
        "prompt": "Do you have a trade-in vehicle, and if so what's it worth?",
        "type": "currency",
        "required": False,
        "validation": {"min": 0, "max": 500000},
        "help_text": "Reduces the amount you need to finance, similar to a deposit.",
    },
    {
        "key": "balloon_payment",
        "prompt": "Would you like a balloon or residual payment at the end of the loan to lower your repayments?",
        "type": "currency",
        "required": False,
        "validation": {"min": 0, "max": 500000},
        "help_text": "A lump sum due at the end of the term instead of being repaid monthly.",
    },
]

PERSONAL_QUESTIONS: list[dict[str, Any]] = [
    {
        "key": "loan_purpose",
        "prompt": "What will you use the loan for?",
        "type": "choice",
        "options": [
            "Debt consolidation",
            "Home improvement",
            "Travel",
            "Medical",
            "Wedding",
            "Education",
            "Other",
        ],
        "required": True,
    },
    {
        "key": "secured",
        "prompt": "Would you like to secure this loan against an asset you own, such as a car?",
        "type": "boolean",
        "required": True,
        "help_text": "A secured personal loan is backed by an asset and often has a lower rate.",
    },
    {
        "key": "security_asset_type",
        "prompt": "What asset would you like to secure the loan against?",
        "type": "text",
        "required": False,
        "help_text": "Only asked if you'd like the loan secured against an asset.",
        "depends_on": {"key": "secured", "equals": True},
    },
    {
        "key": "security_asset_value",
        "prompt": "What's that asset roughly worth?",
        "type": "currency",
        "required": False,
        "validation": {"min": 0, "max": 5000000},
        "help_text": "Only asked if you'd like the loan secured against an asset.",
        "depends_on": {"key": "secured", "equals": True},
    },
]

BUSINESS_QUESTIONS: list[dict[str, Any]] = [
    {
        "key": "business_name",
        "prompt": "What's the name of your business?",
        "type": "text",
        "required": True,
    },
    {
        "key": "abn",
        "prompt": "What's your business's ABN?",
        "type": "text",
        "required": True,
        "help_text": "The 11-digit Australian Business Number.",
    },
    {
        "key": "business_structure",
        "prompt": "How is the business structured?",
        "type": "choice",
        "options": ["Sole trader", "Partnership", "Company", "Trust"],
        "required": True,
    },
    {
        "key": "years_trading",
        "prompt": "How many years has the business been trading?",
        "type": "number",
        "required": True,
        "validation": {"min": 0, "max": 100},
    },
    {
        "key": "annual_turnover",
        "prompt": "What's the business's annual turnover?",
        "type": "currency",
        "required": True,
        "validation": {"min": 0, "max": 100000000},
    },
    {
        "key": "net_profit",
        "prompt": "What's the business's annual net profit, after expenses?",
        "type": "currency",
        "required": False,
        "validation": {"min": 0, "max": 100000000},
        "help_text": "Used to assess the business's ability to service this loan.",
    },
    {
        "key": "industry",
        "prompt": "What industry is the business in?",
        "type": "text",
        "required": False,
    },
    {
        "key": "employee_count",
        "prompt": "How many people does the business employ?",
        "type": "integer",
        "required": False,
        "validation": {"min": 0, "max": 100000},
    },
    {
        "key": "business_purpose",
        "prompt": "What will the funds be used for?",
        "type": "choice",
        "options": ["Equipment", "Working capital", "Expansion", "Vehicle", "Property", "Other"],
        "required": True,
    },
]

INVESTMENT_QUESTIONS: list[dict[str, Any]] = [
    {
        "key": "property_price",
        "prompt": "What's the approximate purchase price of the investment property?",
        "type": "currency",
        "required": True,
        "validation": {"min": 50000, "max": 10000000},
    },
    {
        "key": "deposit_amount",
        "prompt": "How much deposit do you have available?",
        "type": "currency",
        "required": True,
        "validation": {"min": 0, "max": 10000000},
    },
    {
        "key": "expected_rental_income",
        "prompt": "What weekly rental income do you expect?",
        "type": "currency",
        "required": True,
        "validation": {"min": 0, "max": 10000},
    },
    {
        "key": "existing_investment_properties",
        "prompt": "How many investment properties do you already own?",
        "type": "integer",
        "required": True,
        "validation": {"min": 0, "max": 50},
    },
    {
        "key": "property_state",
        "prompt": "Which state or territory is the property in?",
        "type": "choice",
        "options": ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"],
        "required": True,
    },
    {
        "key": "interest_only",
        "prompt": "Would you like an interest-only period on this loan?",
        "type": "boolean",
        "required": True,
        "help_text": "Lowers repayments for a set period by not paying down the principal.",
    },
]

QUESTION_TEMPLATES: list[tuple[LoanType | None, list[dict[str, Any]]]] = [
    (None, BASELINE_QUESTIONS),
    (LoanType.home, HOME_QUESTIONS),
    (LoanType.car, CAR_QUESTIONS),
    (LoanType.personal, PERSONAL_QUESTIONS),
    (LoanType.business, BUSINESS_QUESTIONS),
    (LoanType.investment, INVESTMENT_QUESTIONS),
]

# 5 C's risk-assessment field checklist — dotted `key` paths into the normalised
# application (see schemas/application.py). `five_c` names which C the field feeds;
# `requirement` is "required" (a fatal gap for that C) or "confidence" (present improves
# confidence but its absence isn't fatal).
BASELINE_REQUIRED_FIELDS: list[dict[str, Any]] = [
    {
        "key": "applicant.name",
        "five_c": "character",
        "requirement": "required",
        "label": "Applicant name",
    },
    {
        "key": "applicant.dob",
        "five_c": "character",
        "requirement": "required",
        "label": "Date of birth",
    },
    {
        "key": "applicant.address",
        "five_c": "character",
        "requirement": "required",
        "label": "Address",
    },
    {
        "key": "applicant.employment.status",
        "five_c": "conditions",
        "requirement": "required",
        "label": "Employment status",
    },
    {
        "key": "applicant.employment.income",
        "five_c": "capacity",
        "requirement": "required",
        "label": "Income",
    },
    {
        "key": "applicant.employment.income_frequency",
        "five_c": "capacity",
        "requirement": "confidence",
        "label": "Income frequency",
    },
    {
        "key": "applicant.monthly_expenses",
        "five_c": "capacity",
        "requirement": "confidence",
        "label": "Monthly expenses",
    },
    {
        "key": "loan.amount",
        "five_c": "capacity",
        "requirement": "required",
        "label": "Requested loan amount",
    },
    {
        "key": "loan.purpose",
        "five_c": "conditions",
        "requirement": "required",
        "label": "Loan purpose",
    },
    {
        "key": "loan.term_months",
        "five_c": "capacity",
        "requirement": "confidence",
        "label": "Loan term",
    },
]

COLLATERAL_REQUIRED_FIELDS: list[dict[str, Any]] = [
    {
        "key": "collateral.asset_type",
        "five_c": "collateral",
        "requirement": "required",
        "label": "Asset type",
    },
    {
        "key": "collateral.estimated_value",
        "five_c": "collateral",
        "requirement": "required",
        "label": "Estimated asset value",
    },
    {
        "key": "collateral.deposit_amount",
        "five_c": "capital",
        "requirement": "required",
        "label": "Deposit / savings amount",
    },
]

BUSINESS_REQUIRED_FIELDS: list[dict[str, Any]] = [
    {"key": "business.abn", "five_c": "conditions", "requirement": "required", "label": "ABN"},
    {
        "key": "business.entity_name",
        "five_c": "conditions",
        "requirement": "confidence",
        "label": "Entity name",
    },
    {
        "key": "business.net_profit",
        "five_c": "capacity",
        "requirement": "confidence",
        "label": "Net profit",
    },
    {
        "key": "business.annual_turnover",
        "five_c": "capacity",
        "requirement": "confidence",
        "label": "Annual turnover",
    },
    {
        "key": "business.industry",
        "five_c": "conditions",
        "requirement": "confidence",
        "label": "Industry",
    },
]

# Car loans are unconditionally secured by the vehicle, so these are safe to mark required
# (unlike personal loans, which are only sometimes secured — see the deliberate absence of a
# personal-loan collateral checklist below).
CAR_REQUIRED_FIELDS: list[dict[str, Any]] = [
    {
        "key": "collateral.asset_type",
        "five_c": "collateral",
        "requirement": "required",
        "label": "Vehicle type",
    },
    {
        "key": "collateral.estimated_value",
        "five_c": "collateral",
        "requirement": "required",
        "label": "Vehicle value",
    },
]

REQUIRED_FIELD_TEMPLATES: list[tuple[LoanType | None, list[dict[str, Any]]]] = [
    (None, BASELINE_REQUIRED_FIELDS),
    (LoanType.home, COLLATERAL_REQUIRED_FIELDS),
    (LoanType.investment, COLLATERAL_REQUIRED_FIELDS),
    (LoanType.business, BUSINESS_REQUIRED_FIELDS),
    (LoanType.car, CAR_REQUIRED_FIELDS),
]

PROMPT_CONTENT = """You are a loan broker for {{bank_name}}.

You are guiding a customer through an initial loan enquiry in three stages.

Stage 1 — Greet them warmly and briefly, then ask what they'd like the loan for so you can identify the loan type. Available products:
{{products}}

Stage 2 — Once the loan type is known, you will be given ONE question at a time to ask. Ask exactly that question, in your own natural phrasing, and nothing more. Do not ask several questions at once. Do not skip ahead. Do not invent questions of your own. If the customer's answer is unclear or doesn't fit the question, ask them to clarify that same question rather than moving on.

Stage 3 — When told the questions are complete, summarise back everything you collected and the product you recommended, and tell them a loan specialist will review their enquiry.

Rules:
- Only mention products from the list above. Never invent a product, an interest rate or a limit.
- Explain any financial term in plain language.
- Do not assess eligibility, calculate borrowing capacity, approve, decline, or imply any outcome.
- Do not ask for identity documents, tax file numbers, bank account numbers or passwords.
- If asked something outside a loan enquiry, briefly redirect to the enquiry.
"""

# Appended to the baseline prompt once the loan type is known (agents/prompts/loader.py
# merges baseline + loan-type-specific content) — shifts what the agent emphasises without
# changing the stage 1/2/3 mechanics above.
HOME_PROMPT_FOCUS = """LOAN FOCUS — Home Loan: Prioritise understanding the property being purchased or refinanced — its price, location and type, and whether this is a first home or a refinance. Sound like a home lending specialist who's genuinely interested in the property, not just the numbers."""

INVESTMENT_PROMPT_FOCUS = """LOAN FOCUS — Investment Loan: Prioritise understanding the investment property and the applicant's rental income strategy — expected rent, whether they want an interest-only period, and their existing property portfolio. Sound like an investment lending specialist thinking about portfolio growth, not a single purchase."""

PERSONAL_PROMPT_FOCUS = """LOAN FOCUS — Personal Loan: Prioritise understanding what the funds are for and whether the applicant wants to secure the loan against an asset they own. Keep the tone practical and reassuring — personal loan applicants are often consolidating debt or funding a life event, not making an investment decision."""

CAR_PROMPT_FOCUS = """LOAN FOCUS — Car Loan: Prioritise understanding the vehicle itself — its price and condition, whether there's a trade-in, and whether the applicant wants a balloon or residual payment to lower repayments. Sound like a vehicle finance specialist."""

BUSINESS_PROMPT_FOCUS = """LOAN FOCUS — Business Loan: Prioritise understanding the business itself — its ABN, structure, trading history, turnover and profitability, industry, and any existing business debt or security offered. Sound like a business lending specialist focused on the business's financial track record, not just the applicant's personal finances."""

PROMPT_TEMPLATES: list[tuple[LoanType | None, str]] = [
    (None, PROMPT_CONTENT),
    (LoanType.home, HOME_PROMPT_FOCUS),
    (LoanType.investment, INVESTMENT_PROMPT_FOCUS),
    (LoanType.personal, PERSONAL_PROMPT_FOCUS),
    (LoanType.car, CAR_PROMPT_FOCUS),
    (LoanType.business, BUSINESS_PROMPT_FOCUS),
]

# Development-only credentials. Every seeded account below shares this password so the
# customer and officer portals have something to log in with locally.
# THESE MUST NEVER EXIST IN A DEPLOYED ENVIRONMENT — if you're setting up staging or
# production, skip this seed step (or gate it behind an environment check) rather than
# running it against a real database.
DEMO_PASSWORD = "Demo1234!"

DEMO_USERS: list[dict[str, Any]] = [
    {"email": "customer1@example.com", "name": "Sarah Chen", "role": UserRole.customer},
    {"email": "customer2@example.com", "name": "Michael Nguyen", "role": UserRole.customer},
    {"email": "customer3@example.com", "name": "Priya Sharma", "role": UserRole.customer},
    {"email": "officer@demomutual.test", "name": "James Wilson", "role": UserRole.loan_officer},
    {"email": "manager@demomutual.test", "name": "Angela Brooks", "role": UserRole.credit_manager},
    # Platform-level admin — no bank_id (see _upsert_users).
    {"email": "admin@demomutual.test", "name": "Platform Admin", "role": UserRole.admin},
]

# customer_email + product_name is this table's de-facto natural key for idempotent
# seeding, since applications have no unique business column of their own. days_ago spreads
# created_at across the past few weeks so ordering is visible in both portals.
SEED_APPLICATIONS: list[dict[str, Any]] = [
    {
        "customer_email": "customer1@example.com",
        "product_name": "Standard Home Loan",
        "status": ApplicationStatus.submitted,
        "loan_amount": Decimal("450000"),
        "loan_term_months": 300,
        "purpose": "Purchase of family home",
        "days_ago": 3,
    },
    {
        "customer_email": "customer1@example.com",
        "product_name": "Car Loan",
        "status": ApplicationStatus.decided,
        "loan_amount": Decimal("28000"),
        "loan_term_months": 60,
        "purpose": "New car purchase",
        "days_ago": 20,
    },
    {
        "customer_email": "customer2@example.com",
        "product_name": "Personal Loan",
        "status": ApplicationStatus.draft,
        "loan_amount": Decimal("12000"),
        "loan_term_months": 36,
        "purpose": "Debt consolidation",
        "days_ago": 1,
    },
    {
        "customer_email": "customer2@example.com",
        "product_name": "Investment Home Loan",
        "status": ApplicationStatus.in_review,
        "loan_amount": Decimal("620000"),
        "loan_term_months": 360,
        "purpose": "Investment property purchase",
        "days_ago": 10,
    },
    {
        "customer_email": "customer2@example.com",
        "product_name": "Business Loan",
        "status": ApplicationStatus.decided,
        "loan_amount": Decimal("85000"),
        "loan_term_months": 60,
        "purpose": "Equipment purchase",
        "days_ago": 25,
    },
    {
        "customer_email": "customer3@example.com",
        "product_name": "Personal Loan",
        "status": ApplicationStatus.submitted,
        "loan_amount": Decimal("8000"),
        "loan_term_months": 24,
        "purpose": "Wedding",
        "days_ago": 5,
    },
    {
        "customer_email": "customer3@example.com",
        "product_name": "Car Loan",
        "status": ApplicationStatus.in_review,
        "loan_amount": Decimal("35000"),
        "loan_term_months": 72,
        "purpose": "Used vehicle purchase",
        "days_ago": 14,
    },
    {
        "customer_email": "customer3@example.com",
        "product_name": "Standard Home Loan",
        "status": ApplicationStatus.draft,
        "loan_amount": Decimal("380000"),
        "loan_term_months": 300,
        "purpose": "First home purchase",
        "days_ago": 2,
    },
]

# Keyed by (customer_email, product_name) matching a SEED_APPLICATIONS row — exercises both
# the approve and reject paths, and the customer/officer reason-visibility split (see
# routers/applications.py) with real seeded data, not just tests.
SEED_OFFICER_ACTIONS: dict[tuple[str, str], dict[str, Any]] = {
    ("customer1@example.com", "Car Loan"): {
        "officer_email": "officer@demomutual.test",
        "action": OfficerActionType.approve,
        "reason": None,
    },
    ("customer2@example.com", "Business Loan"): {
        "officer_email": "officer@demomutual.test",
        "action": OfficerActionType.reject,
        "reason": (
            "Insufficient trading history and declared turnover does not support the "
            "requested loan amount."
        ),
    },
}


async def _get_or_create_bank(db: AsyncSession) -> Bank:
    result = await db.execute(select(Bank).where(Bank.slug == DEMO_BANK_SLUG))
    bank = result.scalar_one_or_none()
    if bank is not None:
        bank.name = "Demo Mutual Bank"
        bank.branding = {"primary_color": "#0F6E56", "logo_url": "/logos/demo.svg"}
        bank.status = BankStatus.active
        return bank

    bank = Bank(
        name="Demo Mutual Bank",
        slug=DEMO_BANK_SLUG,
        branding={"primary_color": "#0F6E56", "logo_url": "/logos/demo.svg"},
        status=BankStatus.active,
    )
    db.add(bank)
    await db.flush()
    return bank


async def _upsert_products(db: AsyncSession, bank: Bank) -> None:
    for spec in PRODUCTS:
        result = await db.execute(
            select(LoanProduct).where(
                LoanProduct.bank_id == bank.id, LoanProduct.name == spec["name"]
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            for key, value in spec.items():
                setattr(existing, key, value)
            existing.active = True
        else:
            db.add(LoanProduct(bank_id=bank.id, active=True, **spec))


async def _upsert_question_template(
    db: AsyncSession, loan_type: LoanType | None, questions: list[dict[str, Any]]
) -> None:
    loan_type_filter = (
        QuestionTemplate.loan_type == loan_type
        if loan_type is not None
        else QuestionTemplate.loan_type.is_(None)
    )
    result = await db.execute(
        select(QuestionTemplate).where(
            QuestionTemplate.bank_id.is_(None), loan_type_filter, QuestionTemplate.version == 1
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        existing.questions = questions
        existing.is_active = True
    else:
        db.add(
            QuestionTemplate(
                bank_id=None, loan_type=loan_type, version=1, is_active=True, questions=questions
            )
        )


async def _upsert_required_field_template(
    db: AsyncSession, loan_type: LoanType | None, fields: list[dict[str, Any]]
) -> None:
    loan_type_filter = (
        RequiredFieldTemplate.loan_type == loan_type
        if loan_type is not None
        else RequiredFieldTemplate.loan_type.is_(None)
    )
    result = await db.execute(
        select(RequiredFieldTemplate).where(loan_type_filter, RequiredFieldTemplate.version == 1)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        existing.fields = fields
        existing.is_active = True
    else:
        db.add(RequiredFieldTemplate(loan_type=loan_type, version=1, is_active=True, fields=fields))


async def _upsert_prompt_template(
    db: AsyncSession, loan_type: LoanType | None, content: str
) -> None:
    loan_type_filter = (
        PromptTemplate.loan_type == loan_type
        if loan_type is not None
        else PromptTemplate.loan_type.is_(None)
    )
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.bank_id.is_(None),
            PromptTemplate.agent_name == AGENT_NAME,
            loan_type_filter,
            PromptTemplate.version == 1,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        existing.content = content
        existing.is_active = True
    else:
        db.add(
            PromptTemplate(
                bank_id=None,
                agent_name=AGENT_NAME,
                loan_type=loan_type,
                version=1,
                content=content,
                is_active=True,
            )
        )


async def _upsert_users(db: AsyncSession, bank: Bank) -> dict[str, User]:
    users_by_email: dict[str, User] = {}
    for spec in DEMO_USERS:
        result = await db.execute(select(User).where(User.email == spec["email"]))
        user = result.scalar_one_or_none()
        # Platform-level admins have no bank; every other seeded role belongs to this bank.
        bank_id = None if spec["role"] == UserRole.admin else bank.id

        if user is not None:
            user.name = spec["name"]
            user.role = spec["role"]
            user.bank_id = bank_id
            user.is_active = True
            if user.password_hash is None:
                user.password_hash = hash_password(DEMO_PASSWORD)
        else:
            user = User(
                bank_id=bank_id,
                name=spec["name"],
                email=spec["email"],
                role=spec["role"],
                password_hash=hash_password(DEMO_PASSWORD),
            )
            db.add(user)
            await db.flush()
        users_by_email[spec["email"]] = user
    return users_by_email


async def _upsert_customer_profiles(db: AsyncSession, users_by_email: dict[str, User]) -> None:
    for spec in DEMO_USERS:
        if spec["role"] != UserRole.customer:
            continue
        user = users_by_email[spec["email"]]
        result = await db.execute(select(CustomerProfile).where(CustomerProfile.user_id == user.id))
        if result.scalar_one_or_none() is None:
            db.add(CustomerProfile(user_id=user.id))


async def _upsert_applications(
    db: AsyncSession, bank: Bank, users_by_email: dict[str, User]
) -> dict[tuple[str, str], Application]:
    applications_by_key: dict[tuple[str, str], Application] = {}
    now = datetime.now(UTC)

    for spec in SEED_APPLICATIONS:
        customer = users_by_email[spec["customer_email"]]
        product_result = await db.execute(
            select(LoanProduct).where(
                LoanProduct.bank_id == bank.id, LoanProduct.name == spec["product_name"]
            )
        )
        product = product_result.scalar_one()

        result = await db.execute(
            select(Application).where(
                Application.customer_id == customer.id,
                Application.product_id == product.id,
                Application.loan_amount == spec["loan_amount"],
            )
        )
        application = result.scalar_one_or_none()
        if application is not None:
            application.status = spec["status"]
            application.loan_term_months = spec["loan_term_months"]
            application.purpose = spec["purpose"]
        else:
            created_at = now - timedelta(days=spec["days_ago"])
            application = Application(
                bank_id=bank.id,
                customer_id=customer.id,
                product_id=product.id,
                status=spec["status"],
                loan_amount=spec["loan_amount"],
                loan_term_months=spec["loan_term_months"],
                purpose=spec["purpose"],
                created_at=created_at,
                updated_at=created_at,
            )
            db.add(application)
            await db.flush()
        applications_by_key[(spec["customer_email"], spec["product_name"])] = application

    return applications_by_key


async def _upsert_officer_actions(
    db: AsyncSession,
    users_by_email: dict[str, User],
    applications_by_key: dict[tuple[str, str], Application],
) -> None:
    for key, action_spec in SEED_OFFICER_ACTIONS.items():
        application = applications_by_key.get(key)
        if application is None:
            continue
        officer = users_by_email[action_spec["officer_email"]]

        result = await db.execute(
            select(OfficerAction).where(
                OfficerAction.application_id == application.id,
                OfficerAction.officer_id == officer.id,
                OfficerAction.action == action_spec["action"],
            )
        )
        if result.scalar_one_or_none() is None:
            db.add(
                OfficerAction(
                    application_id=application.id,
                    officer_id=officer.id,
                    action=action_spec["action"],
                    reason=action_spec["reason"],
                )
            )


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        bank = await _get_or_create_bank(db)
        await _upsert_products(db, bank)
        for loan_type, questions in QUESTION_TEMPLATES:
            await _upsert_question_template(db, loan_type, questions)
        for loan_type, fields in REQUIRED_FIELD_TEMPLATES:
            await _upsert_required_field_template(db, loan_type, fields)
        for loan_type, content in PROMPT_TEMPLATES:
            await _upsert_prompt_template(db, loan_type, content)
        users_by_email = await _upsert_users(db, bank)
        await _upsert_customer_profiles(db, users_by_email)
        applications_by_key = await _upsert_applications(db, bank, users_by_email)
        await _upsert_officer_actions(db, users_by_email, applications_by_key)
        await db.commit()
    print("Seed data applied.")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
