from decimal import Decimal

from schemas.application import NormalizedApplication
from schemas.risk_assessment import FiveCField

# Synthetic development placeholders — not real cost-of-living or lending benchmarks.
BENCHMARK_MONTHLY_EXPENSES = Decimal("2500")
BENCHMARK_ANNUAL_INTEREST_RATE = Decimal("0.08")
CREDIT_CARD_MIN_REPAYMENT_RATE = Decimal("0.03")
BNPL_MIN_REPAYMENT_RATE = Decimal("0.05")

_FREQUENCY_TO_MONTHLY_MULTIPLIER: dict[str, Decimal] = {
    "weekly": Decimal(52) / Decimal(12),
    "fortnightly": Decimal(26) / Decimal(12),
    "biweekly": Decimal(26) / Decimal(12),
    "monthly": Decimal(1),
    "annually": Decimal(1) / Decimal(12),
    "annual": Decimal(1) / Decimal(12),
    "yearly": Decimal(1) / Decimal(12),
}


def _monthly_income(income: Decimal, frequency: str | None) -> tuple[Decimal, bool]:
    """Returns (monthly_income, frequency_was_assumed)."""
    multiplier = _FREQUENCY_TO_MONTHLY_MULTIPLIER.get((frequency or "").strip().lower())
    if multiplier is None:
        return income, True
    return income * multiplier, False


def _business_income(app: NormalizedApplication) -> tuple[Decimal, list[str]] | None:
    """For business loans with a declared net profit, capacity is based on the business's
    own cash flow rather than the applicant's personal income — full replacement, not a
    blend, since for a self-employed/business applicant the two figures are frequently the
    same dollars counted twice."""
    product_type = (app.loan.product_type or "").strip().lower()
    if product_type != "business":
        return None
    if app.business.net_profit is None or app.business.net_profit <= 0:
        return None

    notes = [
        "Capacity assessed from the business's declared net profit rather than the "
        "applicant's personal income, to avoid double-counting owner earnings on a "
        "business loan.",
        "Existing business debt (loans, overdrafts) is not currently collected or netted "
        "against this figure.",
    ]
    return app.business.net_profit / Decimal(12), notes


def _personal_income(app: NormalizedApplication) -> tuple[Decimal, list[str]] | None:
    employment = app.applicant.employment
    if employment.income is None or employment.income <= 0:
        return None

    monthly_income, frequency_assumed = _monthly_income(
        employment.income, employment.income_frequency
    )
    notes = []
    if frequency_assumed:
        notes.append("Income frequency not provided — the declared income was treated as monthly.")
    return monthly_income, notes


def _estimated_monthly_repayment(
    principal: Decimal, term_months: int, annual_rate: Decimal
) -> Decimal:
    """Standard amortising-loan monthly repayment."""
    monthly_rate = annual_rate / Decimal(12)
    if monthly_rate == 0:
        return principal / term_months
    factor = (1 + monthly_rate) ** term_months
    return principal * monthly_rate * factor / (factor - 1)


def _new_loan_monthly_repayment(app: NormalizedApplication) -> tuple[Decimal | None, str | None]:
    """Returns (estimated_monthly_repayment, note). Accounts for interest-only (investment)
    and balloon/residual (car) repayment structures, which materially change the figure."""
    if app.loan.amount is None or not app.loan.term_months:
        if app.loan.amount is not None:
            return None, (
                "Loan term not provided — the servicing position for the new loan could not "
                "be estimated."
            )
        return None, None

    if app.loan.interest_only:
        monthly_rate = BENCHMARK_ANNUAL_INTEREST_RATE / Decimal(12)
        repayment = app.loan.amount * monthly_rate
        note = (
            f"New loan repayment estimated as interest-only at a benchmark "
            f"{BENCHMARK_ANNUAL_INTEREST_RATE:.0%} p.a. — no product-specific rate was supplied."
        )
        return repayment, note

    balloon = (
        app.loan.balloon_payment
        if app.loan.balloon_payment and app.loan.balloon_payment > 0
        else None
    )
    amortising_principal = (app.loan.amount - balloon) if balloon is not None else app.loan.amount
    repayment = _estimated_monthly_repayment(
        amortising_principal, app.loan.term_months, BENCHMARK_ANNUAL_INTEREST_RATE
    )
    if balloon is not None:
        note = (
            f"New loan repayment amortises ${amortising_principal:,.0f} (loan amount less a "
            f"${balloon:,.0f} balloon/residual payment) at a benchmark "
            f"{BENCHMARK_ANNUAL_INTEREST_RATE:.0%} p.a. — no product-specific rate was supplied."
        )
    else:
        note = (
            f"New loan repayment estimated at a benchmark {BENCHMARK_ANNUAL_INTEREST_RATE:.0%} "
            "p.a. — no product-specific interest rate was supplied."
        )
    return repayment, note


def _num(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


def calculate_capacity(app: NormalizedApplication) -> FiveCField:
    """Net disposable income and loan-servicing position, computed arithmetically from
    declared income/expenses/debts — never a model output. Any benchmark figure substituted
    for missing or implausible declared data is called out explicitly in `notes`."""
    income_result = _business_income(app) or _personal_income(app)
    if income_result is None:
        return FiveCField(
            value=None,
            source="unavailable",
            confidence="low",
            notes="No declared income (personal or business) — capacity cannot be calculated.",
        )
    monthly_income, notes = income_result
    notes = list(notes)

    if app.applicant.monthly_expenses is not None and app.applicant.monthly_expenses > 0:
        monthly_expenses = app.applicant.monthly_expenses
    else:
        monthly_expenses = BENCHMARK_MONTHLY_EXPENSES
        notes.append(
            f"Declared monthly expenses absent or implausibly low — a benchmark figure of "
            f"${BENCHMARK_MONTHLY_EXPENSES:,.0f}/month was used instead."
        )

    existing_debt_monthly = Decimal("0")
    estimated_revolving_repayment = False
    for loan in app.existing_debt.loans:
        if loan.monthly_repayment is not None:
            existing_debt_monthly += loan.monthly_repayment
    for card in app.existing_debt.credit_cards:
        if card.balance is not None:
            existing_debt_monthly += card.balance * CREDIT_CARD_MIN_REPAYMENT_RATE
            estimated_revolving_repayment = True
    for bnpl in app.existing_debt.bnpl_accounts:
        if bnpl.balance is not None:
            existing_debt_monthly += bnpl.balance * BNPL_MIN_REPAYMENT_RATE
            estimated_revolving_repayment = True
    if estimated_revolving_repayment:
        notes.append(
            "Credit card and/or BNPL monthly repayments were not declared — estimated as a "
            "percentage of the outstanding balance."
        )

    new_loan_monthly, new_loan_note = _new_loan_monthly_repayment(app)
    if new_loan_note:
        notes.append(new_loan_note)

    total_commitments = existing_debt_monthly + (new_loan_monthly or Decimal("0"))
    disposable_income = monthly_income - monthly_expenses - total_commitments
    servicing_ratio = (total_commitments / monthly_income) if monthly_income > 0 else None

    return FiveCField(
        value={
            "monthly_income": _num(monthly_income),
            "monthly_expenses": _num(monthly_expenses),
            "existing_debt_monthly": _num(existing_debt_monthly),
            "new_loan_estimated_monthly_repayment": (
                _num(new_loan_monthly) if new_loan_monthly is not None else None
            ),
            "disposable_income_monthly": _num(disposable_income),
            "servicing_ratio": (
                round(float(servicing_ratio), 4) if servicing_ratio is not None else None
            ),
        },
        source="calculated",
        confidence="medium",
        notes=" ".join(notes) if notes else None,
    )
