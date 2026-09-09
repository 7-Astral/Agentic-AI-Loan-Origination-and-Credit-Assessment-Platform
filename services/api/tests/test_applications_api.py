import json
import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import delete

from auth.security import create_access_token
from core.database import AsyncSessionLocal, engine
from main import app
from models.application import Application
from models.bank import Bank
from models.customer_profile import CustomerProfile
from models.enums import ApplicationStatus, BankStatus, LoanType, UserRole
from models.loan_product import LoanProduct
from models.officer_action import OfficerAction
from models.user import User


async def _create_bank(name: str = "App Test Bank") -> uuid.UUID:
    async with AsyncSessionLocal() as db:
        bank = Bank(
            name=name,
            slug=f"app-test-{uuid.uuid4().hex[:8]}",
            branding={"primary_color": "#444444", "logo_url": "/x.svg"},
            status=BankStatus.active,
        )
        db.add(bank)
        await db.commit()
        return bank.id


async def _create_product(bank_id: uuid.UUID) -> uuid.UUID:
    async with AsyncSessionLocal() as db:
        product = LoanProduct(
            bank_id=bank_id,
            name="Test Personal Loan",
            type=LoanType.personal,
            interest_rate=Decimal("7.500"),
            min_amount=Decimal("1000.00"),
            max_amount=Decimal("50000.00"),
            min_term_months=6,
            max_term_months=60,
            eligibility_rules={},
        )
        db.add(product)
        await db.commit()
        return product.id


async def _create_user(
    bank_id: uuid.UUID | None, role: UserRole = UserRole.customer, is_active: bool = True
) -> uuid.UUID:
    async with AsyncSessionLocal() as db:
        user = User(
            bank_id=bank_id,
            name="Test User",
            email=f"{role.value}-{uuid.uuid4().hex[:8]}@test.local",
            role=role,
            is_active=is_active,
        )
        db.add(user)
        await db.commit()
        return user.id


async def _create_application(
    *,
    bank_id: uuid.UUID,
    customer_id: uuid.UUID,
    product_id: uuid.UUID,
    status: ApplicationStatus = ApplicationStatus.submitted,
    loan_amount: Decimal = Decimal("10000.00"),
) -> uuid.UUID:
    async with AsyncSessionLocal() as db:
        application = Application(
            bank_id=bank_id,
            customer_id=customer_id,
            product_id=product_id,
            status=status,
            loan_amount=loan_amount,
            loan_term_months=24,
            purpose="Test purpose",
        )
        db.add(application)
        await db.commit()
        return application.id


def _token(user_id: uuid.UUID, role: UserRole, bank_id: uuid.UUID | None) -> str:
    return create_access_token(
        sub=str(user_id),
        email="x@test.local",
        name="Test",
        role=role.value,
        bank_id=str(bank_id) if bank_id is not None else None,
    )


async def _cleanup(
    *,
    user_ids: list[uuid.UUID] | None = None,
    bank_ids: list[uuid.UUID] | None = None,
    application_ids: list[uuid.UUID] | None = None,
    product_ids: list[uuid.UUID] | None = None,
) -> None:
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        for application_id in application_ids or []:
            await db.execute(
                delete(OfficerAction).where(OfficerAction.application_id == application_id)
            )
            await db.execute(delete(Application).where(Application.id == application_id))
        for user_id in user_ids or []:
            await db.execute(delete(CustomerProfile).where(CustomerProfile.user_id == user_id))
            await db.execute(delete(User).where(User.id == user_id))
        for product_id in product_ids or []:
            await db.execute(delete(LoanProduct).where(LoanProduct.id == product_id))
        for bank_id in bank_ids or []:
            await db.execute(delete(Bank).where(Bank.id == bank_id))
        await db.commit()


async def test_customer_cannot_read_another_customers_application() -> None:
    bank_id = await _create_bank()
    product_id = await _create_product(bank_id)
    owner_id = await _create_user(bank_id, UserRole.customer)
    other_id = await _create_user(bank_id, UserRole.customer)
    application_id = await _create_application(
        bank_id=bank_id, customer_id=owner_id, product_id=product_id
    )
    other_token = _token(other_id, UserRole.customer, bank_id)

    await engine.dispose()
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/applications/{application_id}",
                headers={"Authorization": f"Bearer {other_token}"},
            )
        assert response.status_code == 403
    finally:
        await _cleanup(
            user_ids=[owner_id, other_id],
            application_ids=[application_id],
            product_ids=[product_id],
            bank_ids=[bank_id],
        )


async def test_officer_cannot_read_application_from_a_different_bank() -> None:
    bank_id = await _create_bank()
    other_bank_id = await _create_bank("Other Bank")
    product_id = await _create_product(bank_id)
    customer_id = await _create_user(bank_id, UserRole.customer)
    officer_id = await _create_user(other_bank_id, UserRole.loan_officer)
    application_id = await _create_application(
        bank_id=bank_id, customer_id=customer_id, product_id=product_id
    )
    officer_token = _token(officer_id, UserRole.loan_officer, other_bank_id)

    await engine.dispose()
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/applications/{application_id}",
                headers={"Authorization": f"Bearer {officer_token}"},
            )
        assert response.status_code == 403
    finally:
        await _cleanup(
            user_ids=[customer_id, officer_id],
            application_ids=[application_id],
            product_ids=[product_id],
            bank_ids=[bank_id, other_bank_id],
        )


async def test_list_applications_scopes_by_role_both_ways() -> None:
    bank_id = await _create_bank()
    other_bank_id = await _create_bank("Other Bank")
    product_id = await _create_product(bank_id)
    other_product_id = await _create_product(other_bank_id)
    customer_id = await _create_user(bank_id, UserRole.customer)
    other_customer_id = await _create_user(bank_id, UserRole.customer)
    outside_customer_id = await _create_user(other_bank_id, UserRole.customer)
    officer_id = await _create_user(bank_id, UserRole.loan_officer)

    own_application_id = await _create_application(
        bank_id=bank_id,
        customer_id=customer_id,
        product_id=product_id,
        status=ApplicationStatus.submitted,
    )
    bankmate_application_id = await _create_application(
        bank_id=bank_id,
        customer_id=other_customer_id,
        product_id=product_id,
        status=ApplicationStatus.in_review,
    )
    outside_application_id = await _create_application(
        bank_id=other_bank_id,
        customer_id=outside_customer_id,
        product_id=other_product_id,
        status=ApplicationStatus.submitted,
    )

    customer_token = _token(customer_id, UserRole.customer, bank_id)
    officer_token = _token(officer_id, UserRole.loan_officer, bank_id)

    await engine.dispose()
    try:
        with TestClient(app) as client:
            customer_response = client.get(
                "/applications", headers={"Authorization": f"Bearer {customer_token}"}
            )
            assert customer_response.status_code == 200
            customer_ids = {row["id"] for row in customer_response.json()}
            assert customer_ids == {str(own_application_id)}

            officer_response = client.get(
                "/applications", headers={"Authorization": f"Bearer {officer_token}"}
            )
            assert officer_response.status_code == 200
            officer_ids = {row["id"] for row in officer_response.json()}
            assert officer_ids == {str(own_application_id), str(bankmate_application_id)}
            assert str(outside_application_id) not in officer_ids

            filtered_response = client.get(
                "/applications?status=in_review",
                headers={"Authorization": f"Bearer {officer_token}"},
            )
            assert filtered_response.status_code == 200
            filtered_ids = {row["id"] for row in filtered_response.json()}
            assert filtered_ids == {str(bankmate_application_id)}
    finally:
        await _cleanup(
            user_ids=[customer_id, other_customer_id, outside_customer_id, officer_id],
            application_ids=[
                own_application_id,
                bankmate_application_id,
                outside_application_id,
            ],
            product_ids=[product_id, other_product_id],
            bank_ids=[bank_id, other_bank_id],
        )


async def test_reject_and_override_require_a_reason_server_side() -> None:
    bank_id = await _create_bank()
    product_id = await _create_product(bank_id)
    customer_id = await _create_user(bank_id, UserRole.customer)
    officer_id = await _create_user(bank_id, UserRole.loan_officer)
    application_id = await _create_application(
        bank_id=bank_id,
        customer_id=customer_id,
        product_id=product_id,
        status=ApplicationStatus.submitted,
    )
    officer_token = _token(officer_id, UserRole.loan_officer, bank_id)

    await engine.dispose()
    try:
        with TestClient(app) as client:
            reject_missing = client.post(
                f"/applications/{application_id}/actions",
                headers={"Authorization": f"Bearer {officer_token}"},
                json={"action": "reject"},
            )
            assert reject_missing.status_code == 422

            reject_blank = client.post(
                f"/applications/{application_id}/actions",
                headers={"Authorization": f"Bearer {officer_token}"},
                json={"action": "reject", "reason": "   "},
            )
            assert reject_blank.status_code == 422

            override_missing = client.post(
                f"/applications/{application_id}/actions",
                headers={"Authorization": f"Bearer {officer_token}"},
                json={"action": "override"},
            )
            assert override_missing.status_code == 422
    finally:
        await _cleanup(
            user_ids=[customer_id, officer_id],
            application_ids=[application_id],
            product_ids=[product_id],
            bank_ids=[bank_id],
        )


async def test_approve_writes_officer_action_and_updates_status() -> None:
    bank_id = await _create_bank()
    product_id = await _create_product(bank_id)
    customer_id = await _create_user(bank_id, UserRole.customer)
    officer_id = await _create_user(bank_id, UserRole.loan_officer)
    application_id = await _create_application(
        bank_id=bank_id,
        customer_id=customer_id,
        product_id=product_id,
        status=ApplicationStatus.submitted,
    )
    officer_token = _token(officer_id, UserRole.loan_officer, bank_id)

    await engine.dispose()
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/applications/{application_id}/actions",
                headers={"Authorization": f"Bearer {officer_token}"},
                json={"action": "approve"},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "decided"
            assert len(body["actions"]) == 1
            assert body["actions"][0]["action"] == "approve"
            assert body["actions"][0]["officer_id"] == str(officer_id)

        await engine.dispose()
        async with AsyncSessionLocal() as db:
            application = await db.get(Application, application_id)
            assert application is not None
            assert application.status == ApplicationStatus.decided
    finally:
        await _cleanup(
            user_ids=[customer_id, officer_id],
            application_ids=[application_id],
            product_ids=[product_id],
            bank_ids=[bank_id],
        )


async def test_reject_reason_never_appears_in_customer_view() -> None:
    """Officer-facing reject/override reasons are internal assessment reasoning and must
    never reach a customer response, even though the officer view legitimately includes
    them (see routers/applications.py's `_build_customer_view` vs `_build_officer_view`)."""
    bank_id = await _create_bank()
    product_id = await _create_product(bank_id)
    customer_id = await _create_user(bank_id, UserRole.customer)
    officer_id = await _create_user(bank_id, UserRole.loan_officer)
    application_id = await _create_application(
        bank_id=bank_id,
        customer_id=customer_id,
        product_id=product_id,
        status=ApplicationStatus.submitted,
    )
    officer_token = _token(officer_id, UserRole.loan_officer, bank_id)
    customer_token = _token(customer_id, UserRole.customer, bank_id)
    secret_reason = "Insufficient income verification and undisclosed liabilities."

    await engine.dispose()
    try:
        with TestClient(app) as client:
            reject_response = client.post(
                f"/applications/{application_id}/actions",
                headers={"Authorization": f"Bearer {officer_token}"},
                json={"action": "reject", "reason": secret_reason},
            )
            assert reject_response.status_code == 200

            customer_response = client.get(
                f"/applications/{application_id}",
                headers={"Authorization": f"Bearer {customer_token}"},
            )
            assert customer_response.status_code == 200
            customer_body = customer_response.json()
            assert customer_body["outcome"] == "rejected"
            assert secret_reason not in json.dumps(customer_body)
            assert customer_body["actions"] == []
            assert customer_body["customer_profile"] is None
            assert customer_body["risk_report"] is None
    finally:
        await _cleanup(
            user_ids=[customer_id, officer_id],
            application_ids=[application_id],
            product_ids=[product_id],
            bank_ids=[bank_id],
        )


async def test_deactivated_officer_cannot_act_even_with_a_valid_token() -> None:
    """The token's claims can outlive an account being deactivated (up to
    jwt_access_token_minutes) — the actions endpoint re-checks `is_active` in the database
    for exactly this reason, since it's the one endpoint whose effect outlives the token."""
    bank_id = await _create_bank()
    product_id = await _create_product(bank_id)
    customer_id = await _create_user(bank_id, UserRole.customer)
    officer_id = await _create_user(bank_id, UserRole.loan_officer, is_active=False)
    application_id = await _create_application(
        bank_id=bank_id,
        customer_id=customer_id,
        product_id=product_id,
        status=ApplicationStatus.submitted,
    )
    officer_token = _token(officer_id, UserRole.loan_officer, bank_id)

    await engine.dispose()
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/applications/{application_id}/actions",
                headers={"Authorization": f"Bearer {officer_token}"},
                json={"action": "approve"},
            )
        assert response.status_code == 403
    finally:
        await _cleanup(
            user_ids=[customer_id, officer_id],
            application_ids=[application_id],
            product_ids=[product_id],
            bank_ids=[bank_id],
        )


async def test_admin_sees_all_applications_across_every_bank() -> None:
    """Admins are modelled with bank_id = None (platform-level, see models/user.py), so
    their list view has no single bank to scope by — it's a deliberate, role-based "see
    everything" scope, not a bypass of the ownership rule that applies to every other role."""
    bank_id = await _create_bank()
    other_bank_id = await _create_bank("Other Bank")
    product_id = await _create_product(bank_id)
    other_product_id = await _create_product(other_bank_id)
    customer_id = await _create_user(bank_id, UserRole.customer)
    other_customer_id = await _create_user(other_bank_id, UserRole.customer)
    admin_id = await _create_user(None, UserRole.admin)

    application_id = await _create_application(
        bank_id=bank_id, customer_id=customer_id, product_id=product_id
    )
    other_application_id = await _create_application(
        bank_id=other_bank_id, customer_id=other_customer_id, product_id=other_product_id
    )
    admin_token = _token(admin_id, UserRole.admin, None)

    await engine.dispose()
    try:
        with TestClient(app) as client:
            response = client.get(
                "/applications", headers={"Authorization": f"Bearer {admin_token}"}
            )
        assert response.status_code == 200
        ids = {row["id"] for row in response.json()}
        # This suite runs against a shared dev database (seed data, other tests' fixture
        # rows), so an admin's "see everything" result can't be asserted as an exact set —
        # only that it isn't scoped away the two applications from two different banks.
        assert {str(application_id), str(other_application_id)} <= ids
    finally:
        await _cleanup(
            user_ids=[customer_id, other_customer_id, admin_id],
            application_ids=[application_id, other_application_id],
            product_ids=[product_id, other_product_id],
            bank_ids=[bank_id, other_bank_id],
        )


async def test_admin_gets_the_full_officer_view_but_cannot_act() -> None:
    """Admin oversight is read-only: the detail view carries the same customer_profile/
    risk_report/actions an officer would see, but POST .../actions still 403s since
    require_role() on that endpoint never includes admin."""
    bank_id = await _create_bank()
    product_id = await _create_product(bank_id)
    customer_id = await _create_user(bank_id, UserRole.customer)
    admin_id = await _create_user(None, UserRole.admin)
    application_id = await _create_application(
        bank_id=bank_id, customer_id=customer_id, product_id=product_id
    )
    admin_token = _token(admin_id, UserRole.admin, None)

    await engine.dispose()
    try:
        with TestClient(app) as client:
            detail_response = client.get(
                f"/applications/{application_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert detail_response.status_code == 200
            body = detail_response.json()
            assert "actions" in body
            assert "risk_report" in body

            action_response = client.post(
                f"/applications/{application_id}/actions",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"action": "approve"},
            )
        assert action_response.status_code == 403
    finally:
        await _cleanup(
            user_ids=[customer_id, admin_id],
            application_ids=[application_id],
            product_ids=[product_id],
            bank_ids=[bank_id],
        )
