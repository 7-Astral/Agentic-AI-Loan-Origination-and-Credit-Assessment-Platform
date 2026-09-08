import json
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from auth.security import hash_password
from core.config import settings
from core.database import AsyncSessionLocal, engine
from main import app
from models.bank import Bank
from models.enums import BankStatus, UserRole
from models.user import User

TEST_PASSWORD = "Correct-Horse-1"


async def _create_bank() -> uuid.UUID:
    async with AsyncSessionLocal() as db:
        bank = Bank(
            name="Auth Test Bank",
            slug=f"auth-test-{uuid.uuid4().hex[:8]}",
            branding={"primary_color": "#555555", "logo_url": "/x.svg"},
            status=BankStatus.active,
        )
        db.add(bank)
        await db.commit()
        return bank.id


async def _create_user(
    bank_id: uuid.UUID | None,
    role: UserRole = UserRole.customer,
    password: str = TEST_PASSWORD,
    is_active: bool = True,
) -> tuple[uuid.UUID, str]:
    email = f"{role.value}-{uuid.uuid4().hex[:8]}@test.local"
    async with AsyncSessionLocal() as db:
        user = User(
            bank_id=bank_id,
            name="Test User",
            email=email,
            role=role,
            password_hash=hash_password(password),
            is_active=is_active,
        )
        db.add(user)
        await db.commit()
        return user.id, email


async def _cleanup(*, user_ids: list[uuid.UUID], bank_id: uuid.UUID | None = None) -> None:
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        for user_id in user_ids:
            await db.execute(delete(User).where(User.id == user_id))
        if bank_id is not None:
            await db.execute(delete(Bank).where(Bank.id == bank_id))
        await db.commit()


def _no_password_hash_anywhere(payload: object) -> bool:
    return "password_hash" not in json.dumps(payload)


async def test_login_succeeds_with_correct_password_and_fails_with_wrong() -> None:
    bank_id = await _create_bank()
    user_id, email = await _create_user(bank_id)

    await engine.dispose()
    try:
        with TestClient(app) as client:
            ok = client.post("/auth/login", json={"email": email, "password": TEST_PASSWORD})
            assert ok.status_code == 200
            body = ok.json()
            assert body["user"]["email"] == email
            assert body["user"]["role"] == "customer"
            assert _no_password_hash_anywhere(body)

            wrong = client.post("/auth/login", json={"email": email, "password": "not-it"})
            assert wrong.status_code == 401
            assert _no_password_hash_anywhere(wrong.json())
    finally:
        await _cleanup(user_ids=[user_id], bank_id=bank_id)


async def test_login_fails_for_unknown_email() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/auth/login", json={"email": "nobody@nowhere.test", "password": "x"}
        )
    assert response.status_code == 401


async def test_get_me_returns_authenticated_user_without_password_hash() -> None:
    bank_id = await _create_bank()
    user_id, email = await _create_user(bank_id, role=UserRole.loan_officer)

    await engine.dispose()
    try:
        with TestClient(app) as client:
            login = client.post("/auth/login", json={"email": email, "password": TEST_PASSWORD})
            token = login.json()["access_token"]

            me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert me.status_code == 200
            body = me.json()
            assert body["email"] == email
            assert body["role"] == "loan_officer"
            assert _no_password_hash_anywhere(body)
    finally:
        await _cleanup(user_ids=[user_id], bank_id=bank_id)


async def test_register_ignores_supplied_role_and_always_creates_customer() -> None:
    bank_id = await _create_bank()
    email = f"register-{uuid.uuid4().hex[:8]}@test.local"

    await engine.dispose()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/auth/register",
                json={
                    "name": "New Customer",
                    "email": email,
                    "password": TEST_PASSWORD,
                    "bank_id": str(bank_id),
                    "role": "admin",  # must be silently ignored
                },
            )
        assert response.status_code == 201
        body = response.json()
        assert body["user"]["role"] == "customer"
        assert _no_password_hash_anywhere(body)

        # Confirm what actually landed in the database, not just the response shape.
        await engine.dispose()
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one()
            assert user.role == UserRole.customer
            user_id = user.id
    finally:
        await _cleanup(user_ids=[user_id], bank_id=bank_id)


async def test_register_rejects_duplicate_email() -> None:
    bank_id = await _create_bank()
    user_id, email = await _create_user(bank_id)

    await engine.dispose()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/auth/register",
                json={
                    "name": "Someone Else",
                    "email": email,
                    "password": TEST_PASSWORD,
                    "bank_id": str(bank_id),
                },
            )
        assert response.status_code == 409
    finally:
        await _cleanup(user_ids=[user_id], bank_id=bank_id)


async def test_protected_endpoint_401_without_token() -> None:
    with TestClient(app) as client:
        response = client.get("/applications")
    assert response.status_code == 401


async def test_protected_endpoint_401_with_garbage_token() -> None:
    with TestClient(app) as client:
        response = client.get("/applications", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


async def test_protected_endpoint_401_with_expired_token() -> None:
    expired_payload = {
        "sub": str(uuid.uuid4()),
        "email": "x@test.local",
        "name": "X",
        "role": "customer",
        "bank_id": None,
        "exp": datetime.now(UTC) - timedelta(minutes=1),
    }
    expired_token = jwt.encode(
        expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )

    with TestClient(app) as client:
        response = client.get("/applications", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401


async def test_require_role_403_for_wrong_role() -> None:
    """A customer hitting the officer-only actions endpoint gets 403, not a role check that
    silently no-ops or a 404 that hides the real reason."""
    bank_id = await _create_bank()
    user_id, email = await _create_user(bank_id, role=UserRole.customer)

    await engine.dispose()
    try:
        with TestClient(app) as client:
            login = client.post("/auth/login", json={"email": email, "password": TEST_PASSWORD})
            token = login.json()["access_token"]

            response = client.post(
                f"/applications/{uuid.uuid4()}/actions",
                headers={"Authorization": f"Bearer {token}"},
                json={"action": "approve"},
            )
        assert response.status_code == 403
    finally:
        await _cleanup(user_ids=[user_id], bank_id=bank_id)
