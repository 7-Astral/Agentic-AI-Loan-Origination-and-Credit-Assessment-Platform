from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import LoanType
from models.required_field_template import RequiredFieldTemplate
from schemas.risk_assessment import RequiredField


async def _get_template(
    db: AsyncSession, loan_type: LoanType | None
) -> RequiredFieldTemplate | None:
    """Returns the active required-field template for `loan_type` (None = baseline),
    latest version — same shape as `agents.questions.loader._get_template`."""
    loan_type_filter = (
        RequiredFieldTemplate.loan_type == loan_type
        if loan_type is not None
        else RequiredFieldTemplate.loan_type.is_(None)
    )
    stmt = (
        select(RequiredFieldTemplate)
        .where(RequiredFieldTemplate.is_active.is_(True), loan_type_filter)
        .order_by(RequiredFieldTemplate.version.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_required_fields(db: AsyncSession, loan_type: LoanType | None) -> list[RequiredField]:
    """Returns the merged checklist for `loan_type`: the baseline checklist (loan_type IS
    NULL) followed by the type-specific one. Database-driven — the checklist can change per
    product without a code change. Falls back to the baseline alone when `loan_type` is
    unknown or wasn't supplied, consistent with the agent never blocking on missing data."""
    fields: list[RequiredField] = []

    baseline = await _get_template(db, None)
    if baseline is not None:
        fields.extend(RequiredField.model_validate(item) for item in baseline.fields)

    if loan_type is not None:
        specific = await _get_template(db, loan_type)
        if specific is not None:
            fields.extend(RequiredField.model_validate(item) for item in specific.fields)

    return fields
