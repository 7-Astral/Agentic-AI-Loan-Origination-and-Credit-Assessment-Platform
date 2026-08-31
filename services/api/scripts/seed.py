"""Idempotent seed data for local development.

NOTE: the interest rates, amount limits and term ranges below are synthetic development
placeholders chosen for demo purposes — they are not real product terms and must never be
treated as such.
"""

import asyncio
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal
from models.bank import Bank
from models.enums import BankStatus, LoanType
from models.loan_product import LoanProduct
from models.prompt_template import PromptTemplate
from models.question_template import QuestionTemplate

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
]

BUSINESS_QUESTIONS: list[dict[str, Any]] = [
    {
        "key": "business_name",
        "prompt": "What's the name of your business?",
        "type": "text",
        "required": True,
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
]

QUESTION_TEMPLATES: list[tuple[LoanType | None, list[dict[str, Any]]]] = [
    (None, BASELINE_QUESTIONS),
    (LoanType.home, HOME_QUESTIONS),
    (LoanType.car, CAR_QUESTIONS),
    (LoanType.personal, PERSONAL_QUESTIONS),
    (LoanType.business, BUSINESS_QUESTIONS),
    (LoanType.investment, INVESTMENT_QUESTIONS),
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


async def _upsert_prompt_template(db: AsyncSession) -> None:
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.bank_id.is_(None),
            PromptTemplate.agent_name == AGENT_NAME,
            PromptTemplate.version == 1,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        existing.content = PROMPT_CONTENT
        existing.is_active = True
    else:
        db.add(
            PromptTemplate(
                bank_id=None,
                agent_name=AGENT_NAME,
                version=1,
                content=PROMPT_CONTENT,
                is_active=True,
            )
        )


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        bank = await _get_or_create_bank(db)
        await _upsert_products(db, bank)
        for loan_type, questions in QUESTION_TEMPLATES:
            await _upsert_question_template(db, loan_type, questions)
        await _upsert_prompt_template(db)
        await db.commit()
    print("Seed data applied.")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
