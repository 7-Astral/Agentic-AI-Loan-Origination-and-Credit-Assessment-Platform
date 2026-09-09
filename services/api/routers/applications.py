import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.risk_assessment.orchestrator import assess_application
from auth.dependencies import get_current_user, require_role
from core.database import get_db
from models.application import Application
from models.customer_profile import CustomerProfile
from models.enums import ApplicationStatus, OfficerActionType, UserRole
from models.loan_product import LoanProduct
from models.officer_action import OfficerAction
from models.user import User
from schemas.application_record import (
    ApplicationActionRequest,
    ApplicationDetail,
    ApplicationSummary,
    OfficerActionOut,
    Outcome,
)
from schemas.auth import UserClaims
from schemas.customer_profile import CustomerProfileOut

router = APIRouter(prefix="/applications", tags=["applications"])

_OUTCOME_LABELS: dict[OfficerActionType, Outcome] = {
    OfficerActionType.approve: "approved",
    OfficerActionType.reject: "rejected",
    OfficerActionType.override: "overridden",
}


async def _get_application_or_404(db: AsyncSession, application_id: uuid.UUID) -> Application:
    application = await db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


def _check_customer_ownership(application: Application, user: UserClaims) -> None:
    # All PKs in this schema are uuid4 (non-sequential), so a 403 here leaks no practical
    # enumeration advantage over a uniform 404 — this is the ownership-scoping contract the
    # task requires, applied consistently to every mismatch, not just the named case.
    if application.customer_id != uuid.UUID(user.sub):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")


def _check_bank_ownership(application: Application, user: UserClaims) -> None:
    if user.bank_id is None or application.bank_id != user.bank_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")


async def _load_names(db: AsyncSession, application: Application) -> tuple[str, str]:
    customer = await db.get(User, application.customer_id)
    product = await db.get(LoanProduct, application.product_id)
    return (customer.name if customer else "Unknown"), (product.name if product else "Unknown")


def _summary_fields(
    application: Application, customer_name: str, product_name: str
) -> dict[str, Any]:
    return dict(
        id=application.id,
        bank_id=application.bank_id,
        customer_id=application.customer_id,
        customer_name=customer_name,
        product_id=application.product_id,
        product_name=product_name,
        status=application.status,
        loan_amount=application.loan_amount,
        loan_term_months=application.loan_term_months,
        purpose=application.purpose,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


async def _latest_action(
    db: AsyncSession, application_id: uuid.UUID, actions: tuple[OfficerActionType, ...]
) -> OfficerAction | None:
    stmt = (
        select(OfficerAction)
        .where(OfficerAction.application_id == application_id, OfficerAction.action.in_(actions))
        .order_by(OfficerAction.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def _build_customer_view(db: AsyncSession, application: Application) -> ApplicationDetail:
    """Never serializes officer_actions or their reasons, the risk report, or the customer
    profile — this is a genuinely different, smaller response, not the officer view with
    fields hidden client-side."""
    customer_name, product_name = await _load_names(db, application)

    outcome = None
    info_request_message = None
    if application.status == ApplicationStatus.decided:
        latest = await _latest_action(
            db,
            application.id,
            (OfficerActionType.approve, OfficerActionType.reject, OfficerActionType.override),
        )
        if latest is not None:
            outcome = _OUTCOME_LABELS[latest.action]
        # The reason text for approve/reject/override is intentionally never read here —
        # it must never reach a customer response.
    else:
        latest_info = await _latest_action(db, application.id, (OfficerActionType.request_info,))
        if latest_info is not None:
            info_request_message = latest_info.reason

    return ApplicationDetail(
        **_summary_fields(application, customer_name, product_name),
        outcome=outcome,
        info_request_message=info_request_message,
    )


def _build_risk_input(
    application: Application, profile: CustomerProfile | None, customer: User, product: LoanProduct
) -> dict[str, Any]:
    """Maps the persisted, structured Application/CustomerProfile/User rows into the raw
    JSON shape agents.risk_assessment.normalise expects — a much more direct mapping than
    the chat-based conversation-to-application.ts equivalent, since these fields are already
    structured rather than free-form chat answers."""
    return {
        "applicant": {
            "name": customer.name,
            "employment": {
                "status": profile.employment_status if profile else None,
                "income": float(profile.income) if profile and profile.income is not None else None,
            },
            "monthly_expenses": (
                float(profile.expenses) if profile and profile.expenses is not None else None
            ),
        },
        "loan": {
            "amount": float(application.loan_amount),
            "term_months": application.loan_term_months,
            "purpose": application.purpose,
            "product_type": product.type.value,
        },
        "existing_debt": profile.liabilities if profile else {},
    }


async def _build_officer_view(db: AsyncSession, application: Application) -> ApplicationDetail:
    customer_name, product_name = await _load_names(db, application)

    actions_stmt = (
        select(OfficerAction, User.name)
        .join(User, OfficerAction.officer_id == User.id)
        .where(OfficerAction.application_id == application.id)
        .order_by(OfficerAction.created_at.desc())
    )
    actions_result = await db.execute(actions_stmt)
    actions = [
        OfficerActionOut(
            id=action.id,
            officer_id=action.officer_id,
            officer_name=officer_name,
            action=action.action,
            reason=action.reason,
            created_at=action.created_at,
        )
        for action, officer_name in actions_result.all()
    ]

    profile_result = await db.execute(
        select(CustomerProfile).where(CustomerProfile.user_id == application.customer_id)
    )
    profile = profile_result.scalar_one_or_none()
    customer_profile = CustomerProfileOut.model_validate(profile) if profile is not None else None

    customer = await db.get(User, application.customer_id)
    product = await db.get(LoanProduct, application.product_id)
    risk_report = None
    if customer is not None and product is not None:
        raw_input = _build_risk_input(application, profile, customer, product)
        # Computed live, uncached, deliberately: this is decision support for an
        # irreversible officer_actions write, and must reflect the customer's latest
        # declared profile, not a stale cached figure.
        risk_report = await assess_application(db, raw_input, application_id=str(application.id))

    return ApplicationDetail(
        **_summary_fields(application, customer_name, product_name),
        actions=actions,
        customer_profile=customer_profile,
        risk_report=risk_report,
    )


@router.get("", response_model=list[ApplicationSummary])
async def list_applications(
    status_filter: ApplicationStatus | None = Query(None, alias="status"),
    user: UserClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ApplicationSummary]:
    """Same endpoint for every role, scoped entirely by the authenticated identity — never
    by a client-supplied parameter. A customer gets their own applications; an officer or
    credit manager gets their bank's queue; an admin gets every application, platform-wide
    (admins are modelled with `bank_id = None` — see models/user.py — so there is no single
    bank to scope them to). Status filtering applies to every role except customer, whose
    own application count is small enough that it isn't needed."""
    stmt = (
        select(Application, User.name, LoanProduct.name)
        .join(User, Application.customer_id == User.id)
        .join(LoanProduct, Application.product_id == LoanProduct.id)
    )

    if user.role == UserRole.customer:
        stmt = stmt.where(Application.customer_id == uuid.UUID(user.sub))
    elif user.role in (UserRole.loan_officer, UserRole.credit_manager):
        if user.bank_id is None:
            raise HTTPException(status_code=403, detail="No bank associated with this account")
        stmt = stmt.where(Application.bank_id == user.bank_id)
    elif user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not permitted")

    if status_filter is not None and user.role != UserRole.customer:
        stmt = stmt.where(Application.status == status_filter)

    stmt = stmt.order_by(Application.created_at.desc())
    result = await db.execute(stmt)

    return [
        ApplicationSummary(**_summary_fields(application, customer_name, product_name))
        for application, customer_name, product_name in result.all()
    ]


@router.get("/{application_id}", response_model=ApplicationDetail)
async def get_application(
    application_id: uuid.UUID,
    user: UserClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationDetail:
    application = await _get_application_or_404(db, application_id)

    if user.role == UserRole.customer:
        _check_customer_ownership(application, user)
        return await _build_customer_view(db, application)
    if user.role in (UserRole.loan_officer, UserRole.credit_manager):
        _check_bank_ownership(application, user)
        return await _build_officer_view(db, application)
    if user.role == UserRole.admin:
        # No bank ownership check: an admin has no bank_id to check against by design (see
        # list_applications) and is trusted with platform-wide read-only oversight. Actually
        # acting on an application still requires loan_officer/credit_manager — the actions
        # endpoint's require_role() already excludes admin, so this view being read-only is
        # enforced there, not here.
        return await _build_officer_view(db, application)
    raise HTTPException(status_code=403, detail="Not permitted")


@router.post("/{application_id}/actions", response_model=ApplicationDetail)
async def post_action(
    application_id: uuid.UUID,
    body: ApplicationActionRequest,
    user: UserClaims = Depends(require_role(UserRole.loan_officer, UserRole.credit_manager)),
    db: AsyncSession = Depends(get_db),
) -> ApplicationDetail:
    application = await _get_application_or_404(db, application_id)
    _check_bank_ownership(application, user)

    if body.action in (OfficerActionType.reject, OfficerActionType.override):
        if body.reason is None or not body.reason.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A reason is required for this action",
            )

    # Stale-token carve-out: this is the one endpoint whose effect (an officer_actions row +
    # a status mutation) outlives the token, so it re-checks the acting officer is still
    # active rather than trusting a claim that could be up to jwt_access_token_minutes old.
    officer = await db.get(User, uuid.UUID(user.sub))
    if officer is None or not officer.is_active:
        raise HTTPException(status_code=403, detail="This account is no longer active")

    db.add(
        OfficerAction(
            application_id=application.id,
            officer_id=officer.id,
            action=body.action,
            reason=body.reason,
        )
    )
    application.status = (
        ApplicationStatus.in_review
        if body.action == OfficerActionType.request_info
        else ApplicationStatus.decided
    )
    await db.commit()
    await db.refresh(application)

    return await _build_officer_view(db, application)
