import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agents.risk_assessment.capacity import calculate_capacity
from agents.risk_assessment.checklist_loader import get_required_fields
from agents.risk_assessment.completeness import compute_completeness_score, compute_missing_fields
from agents.risk_assessment.five_cs import (
    calculate_capital,
    calculate_character,
    calculate_collateral,
    calculate_conditions,
)
from agents.risk_assessment.normalise import normalise_application
from integration.abr import AbrResult
from integration.abr import lookup_abn as _default_lookup_abn
from integration.credit_bureau import CreditBureauResult
from integration.credit_bureau import get_credit_report as _default_get_credit_report
from models.enums import LoanType
from schemas.risk_assessment import CompletenessInfo, DataSourceEntry, FiveCs, RiskAssessmentReport

GetCreditReport = Callable[[str, str, str], Awaitable[CreditBureauResult]]
LookupAbn = Callable[[str], Awaitable[AbrResult]]


def _infer_loan_type(product_type: str | None) -> LoanType | None:
    """Best-effort match of the declared product type against the platform's LoanType enum,
    used only to select a more specific required-fields checklist. Never blocks: an
    unrecognised or absent product type just falls back to the baseline checklist."""
    if not product_type:
        return None
    normalized = product_type.strip().lower()
    for candidate in LoanType:
        if candidate.value == normalized:
            return candidate
    return None


async def assess_application(
    db: AsyncSession,
    raw_application: dict[str, Any],
    *,
    application_id: str | None = None,
    get_credit_report: GetCreditReport | None = None,
    lookup_abn: LookupAbn | None = None,
) -> RiskAssessmentReport:
    """Coordinates collection and assembles the 5 C's risk assessment report.

    Collection is conditional and independent: the credit bureau is only called when the
    applicant's name, date of birth and address are all present; the ABR is only called when
    an ABN is present. One collector failing, timing out, or being skipped never prevents
    the others or the report itself from completing — every stage degrades gracefully.

    `get_credit_report`/`lookup_abn` are injection seams for tests (mirroring the
    `llm: LLMProvider | None = None` pattern in agents/orchestrator.py) — production callers
    should omit them and get the real integration.* collectors.

    Returns an assessment, not a decision: no approval, rejection, eligibility verdict or
    overall risk grade is produced here."""
    get_credit_report = get_credit_report or _default_get_credit_report
    lookup_abn = lookup_abn or _default_lookup_abn

    normalized = normalise_application(raw_application)
    loan_type = _infer_loan_type(normalized.loan.product_type)

    required_fields = await get_required_fields(db, loan_type)
    missing_fields = compute_missing_fields(normalized, required_fields)
    completeness_score = compute_completeness_score(required_fields, missing_fields)

    data_sources: list[DataSourceEntry] = []
    applicant = normalized.applicant

    bureau_result: CreditBureauResult | None = None
    if applicant.name and applicant.dob and applicant.address:
        bureau_result = await get_credit_report(
            applicant.name, applicant.dob.isoformat(), applicant.address
        )
        data_sources.append(
            DataSourceEntry(
                source="mock_bureau",
                called=True,
                matched=bureau_result.matched,
                reason=bureau_result.error,
            )
        )
    else:
        data_sources.append(
            DataSourceEntry(
                source="mock_bureau",
                called=False,
                reason="applicant name, date of birth and address are not all present",
            )
        )

    abr_result: AbrResult | None = None
    if normalized.business.abn:
        abr_result = await lookup_abn(normalized.business.abn)
        data_sources.append(
            DataSourceEntry(
                source="abr", called=True, matched=abr_result.found, reason=abr_result.error
            )
        )
    else:
        data_sources.append(DataSourceEntry(source="abr", called=False, reason="no ABN provided"))

    five_cs = FiveCs(
        character=calculate_character(bureau_result),
        capacity=calculate_capacity(normalized),
        capital=calculate_capital(normalized),
        collateral=calculate_collateral(normalized),
        conditions=calculate_conditions(normalized, abr_result),
    )

    # Constructing RiskAssessmentReport validates the assembled report against its schema —
    # a malformed report raises here (fails loudly) rather than reaching the frontend.
    return RiskAssessmentReport(
        application_id=application_id or str(uuid.uuid4()),
        assessed_at=datetime.now(UTC),
        completeness=CompletenessInfo(score=completeness_score, missing_fields=missing_fields),
        five_cs=five_cs,
        data_sources=data_sources,
    )
