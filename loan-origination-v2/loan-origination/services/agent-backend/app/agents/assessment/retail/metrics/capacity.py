from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.agents.assessment.metric import Channel, Metric, MetricState
from app.agents.assessment.retail import bank_analysis
FREQUENCY_PER_YEAR = {"weekly": 52, "fortnightly": 26, "monthly": 12}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _computed(value, channel: Channel, **kwargs) -> Metric:
    return Metric(value=value, state=MetricState.COMPUTED, channel=channel, computed_at=_now(), **kwargs)


def gross_annual_income(filled: dict[str, Any]) -> Metric[Decimal]:
    value = filled.get("gross_annual_income")
    if value is None:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DECLARATION)
    return _computed(Decimal(str(value)), Channel.DECLARATION, unit="AUD/year")


def shaded_income(gross: Metric[Decimal], employment_status: str | None, shading_rates: dict) -> Metric[Decimal]:
    if not gross.usable or employment_status is None:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DERIVED)

    rate = Decimal(str(shading_rates.get(employment_status, 1.0)))
    value = (gross.value * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.DERIVED, unit="AUD/year", inputs={
        "gross_annual_income": float(gross.value), "employment_status": employment_status, "shading_rate": float(rate),
    })


def net_monthly_income(filled: dict[str, Any]) -> Metric[Decimal]:
    amount = filled.get("net_income_amount")
    frequency = filled.get("net_income_frequency")
    if amount is None or frequency not in FREQUENCY_PER_YEAR:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DECLARATION)

    per_year = Decimal(str(amount)) * FREQUENCY_PER_YEAR[frequency]
    value = (per_year / 12).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.DECLARATION, unit="AUD/month", inputs={
        "amount": amount, "frequency": frequency,
    })


def declared_expenses(filled: dict[str, Any]) -> Metric[Decimal]:
    exp_keys = [k for k in filled if k.startswith("exp_")]
    if not exp_keys:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DECLARATION)

    total = sum(Decimal(str(filled[k])) for k in exp_keys)
    return _computed(total, Channel.DECLARATION, unit="AUD/month", inputs={k: filled[k] for k in exp_keys})


def hem_benchmark(filled: dict[str, Any], hem_table: dict) -> Metric[Decimal]:
    dependants = filled.get("dependants")
    marital_status = filled.get("marital_status")
    if dependants is None or marital_status is None:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.BENCHMARK)

    household_size = int(dependants) + (2 if marital_status in ("married", "de_facto") else 1)
    key = str(min(household_size, 5))
    if key not in hem_table:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.BENCHMARK)

    value = Decimal(str(hem_table[key]))
    return _computed(value, Channel.BENCHMARK, unit="AUD/month", inputs={"household_size": household_size})


def assessed_living_expenses(
    declared: Metric[Decimal], verified: Metric[Decimal], hem: Metric[Decimal]
) -> Metric[Decimal]:
    candidates = [m.value for m in (declared, verified, hem) if m.usable]
    if not candidates:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DERIVED)

    value = max(candidates)
    return _computed(value, Channel.DERIVED, unit="AUD/month", inputs={
        "declared": float(declared.value) if declared.usable else None,
        "verified": float(verified.value) if verified.usable else None,
        "hem": float(hem.value) if hem.usable else None,
    })


def existing_commitments(filled: dict[str, Any]) -> Metric[Decimal]:
    other_loans = filled.get("other_loan_repayments_monthly")
    card_limit = filled.get("credit_card_limit_total")
    if other_loans is None and card_limit is None:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DECLARATION)

    total = Decimal(str(other_loans or 0))
    if card_limit:
        total += Decimal(str(card_limit)) * Decimal("0.03")
    return _computed(total, Channel.DERIVED, unit="AUD/month", inputs={
        "other_loan_repayments_monthly": other_loans, "credit_card_limit_total": card_limit,
    })


def assessment_rate(product_rate: float, buffer_pct: float) -> Metric[Decimal]:
    value = Decimal(str(product_rate)) + Decimal(str(buffer_pct))
    return _computed(value, Channel.POLICY, unit="% p.a.", inputs={
        "product_rate": product_rate, "buffer_pct": buffer_pct,
    })


def proposed_repayment(loan_amount: float, term_months: int, rate: Metric[Decimal]) -> Metric[Decimal]:
    if not rate.usable or not loan_amount or not term_months:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DERIVED)

    principal = Decimal(str(loan_amount))
    monthly_rate = (rate.value / 100) / 12
    n = int(term_months)

    if monthly_rate == 0:
        payment = principal / n
    else:
        factor = (1 + monthly_rate) ** n
        payment = principal * monthly_rate * factor / (factor - 1)

    value = payment.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.DERIVED, unit="AUD/month", inputs={
        "loan_amount": loan_amount, "term_months": term_months, "assessment_rate_pct": float(rate.value),
    })


def monthly_surplus(
    income: Metric[Decimal], expenses: Metric[Decimal], commitments: Metric[Decimal], repayment: Metric[Decimal]
) -> Metric[Decimal]:
    inputs = (income, expenses, commitments, repayment)
    if not all(m.usable for m in inputs):
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DERIVED)

    monthly_income = income.value / 12
    value = (monthly_income - expenses.value - commitments.value - repayment.value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return _computed(value, Channel.DERIVED, unit="AUD/month", inputs={
        "monthly_income": float(monthly_income), "expenses": float(expenses.value),
        "commitments": float(commitments.value), "repayment": float(repayment.value),
    })


def nsr(surplus: Metric[Decimal], repayment: Metric[Decimal]) -> Metric[Decimal]:
    if not surplus.usable or not repayment.usable or repayment.value == 0:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DERIVED)

    value = (surplus.value / repayment.value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.DERIVED, unit="ratio", inputs={
        "surplus": float(surplus.value), "repayment": float(repayment.value),
    })


def dti(gross: Metric[Decimal], commitments: Metric[Decimal], repayment: Metric[Decimal]) -> Metric[Decimal]:
    if not gross.usable or not commitments.usable or not repayment.usable or gross.value == 0:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DERIVED)

    total_debt_service_annual = (commitments.value + repayment.value) * 12
    value = (total_debt_service_annual / gross.value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.DERIVED, unit="ratio")


def dsr(income: Metric[Decimal], commitments: Metric[Decimal], repayment: Metric[Decimal]) -> Metric[Decimal]:
    if not income.usable or not commitments.usable or not repayment.usable:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DERIVED)

    monthly_income = income.value / 12
    if monthly_income == 0:
        return Metric(value=None, state=MetricState.UNAVAILABLE, channel=Channel.DERIVED)

    value = ((commitments.value + repayment.value) / monthly_income).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return _computed(value, Channel.DERIVED, unit="ratio")


def assess_capacity(filled: dict[str, Any], product: dict, policy: dict, bank_transactions: list[dict] | None = None) -> dict[str, Metric]:
    gross = gross_annual_income(filled)
    shaded = shaded_income(gross, filled.get("employment_status"), policy["shading_rates"])
    net_income = net_monthly_income(filled)
    declared = declared_expenses(filled)
    verified = bank_analysis.verified_expenses(bank_transactions)
    hem = hem_benchmark(filled, policy["hem_benchmarks"])
    assessed_expenses = assessed_living_expenses(declared, verified, hem)
    commitments = existing_commitments(filled)
    rate = assessment_rate(product["interest_rate"], policy["assessment_rate_buffer"]["buffer_pct"])
    repayment = proposed_repayment(filled.get("loan_amount"), filled.get("loan_term_months"), rate)
    surplus = monthly_surplus(shaded, assessed_expenses, commitments, repayment)
    nsr_result = nsr(surplus, repayment)
    dti_result = dti(shaded, commitments, repayment)
    dsr_result = dsr(shaded, commitments, repayment)

    return {
        "gross_annual_income": gross,
        "shaded_income": shaded,
        "net_monthly_income": net_income,
        "declared_expenses": declared,
        "verified_expenses": verified,
        "hem_benchmark": hem,
        "assessed_living_expenses": assessed_expenses,
        "existing_commitments": commitments,
        "assessment_rate": rate,
        "proposed_repayment": repayment,
        "monthly_surplus": surplus,
        "nsr": nsr_result,
        "dti": dti_result,
        "dsr": dsr_result,
    }