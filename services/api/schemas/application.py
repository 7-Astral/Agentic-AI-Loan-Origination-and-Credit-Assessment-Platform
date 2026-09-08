from datetime import date
from decimal import Decimal

from pydantic import BaseModel

# Canonical, fully-normalised shape an application is coerced into. Every field at every
# level is optional — applications arrive in varying states of completeness, and the
# normaliser (agents/risk_assessment/normalise.py) never rejects incomplete input.
#
# Note: this is the risk-assessment domain's transient input shape — it is never persisted.
# The *persisted* loan application record (status, officer actions, etc.) is a different
# concept living in models/application.py, with its own API schemas in
# schemas/application_record.py (split out specifically to avoid clashing with this file).


class Employment(BaseModel):
    status: str | None = None
    employer: str | None = None
    years_in_role: float | None = None
    income: Decimal | None = None
    income_frequency: str | None = None


class Applicant(BaseModel):
    name: str | None = None
    dob: date | None = None
    address: str | None = None
    employment: Employment = Employment()
    # Not itemised in the platform's own loan-enquiry question set either (see
    # scripts/seed.py: BASELINE_QUESTIONS) — modelled as a top-level applicant figure rather
    # than nested under employment, matching how it's already collected elsewhere.
    monthly_expenses: Decimal | None = None


class Loan(BaseModel):
    amount: Decimal | None = None
    purpose: str | None = None
    term_months: int | None = None
    product_type: str | None = None
    # Interest-only (investment) and balloon/residual (car) repayment structures change the
    # servicing calculation materially — see agents/risk_assessment/capacity.py.
    interest_only: bool | None = None
    balloon_payment: Decimal | None = None


class ExistingLoan(BaseModel):
    type: str | None = None
    balance: Decimal | None = None
    monthly_repayment: Decimal | None = None


class BnplAccount(BaseModel):
    provider: str | None = None
    limit: Decimal | None = None
    balance: Decimal | None = None


class CreditCard(BaseModel):
    limit: Decimal | None = None
    balance: Decimal | None = None


class ExistingDebt(BaseModel):
    loans: list[ExistingLoan] = []
    bnpl_accounts: list[BnplAccount] = []
    credit_cards: list[CreditCard] = []


class Business(BaseModel):
    abn: str | None = None
    entity_name: str | None = None
    industry: str | None = None
    years_trading: float | None = None
    annual_turnover: Decimal | None = None
    # Used by Capacity in preference to the applicant's personal income for business loans,
    # when declared — see agents/risk_assessment/capacity.py.
    net_profit: Decimal | None = None
    employee_count: int | None = None


class Collateral(BaseModel):
    asset_type: str | None = None
    estimated_value: Decimal | None = None
    deposit_amount: Decimal | None = None


class NormalizedApplication(BaseModel):
    applicant: Applicant = Applicant()
    loan: Loan = Loan()
    existing_debt: ExistingDebt = ExistingDebt()
    business: Business = Business()
    collateral: Collateral = Collateral()
