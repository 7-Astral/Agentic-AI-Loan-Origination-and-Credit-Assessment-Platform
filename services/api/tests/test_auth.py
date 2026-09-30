"""Registration/login — the basic identity flow everything else depends on."""
import pytest

from tests.conftest import auth_headers, make_user


async def test_register_creates_customer_and_returns_token(client):
    resp = await client.post(
        "/auth/register",
        json={"email": "new@customer.example", "password": "Passw0rd!23", "full_name": "New Customer"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["role"] == "customer"
    assert body["user"]["email"] == "new@customer.example"
    assert body["access_token"]


async def test_register_duplicate_email_rejected(client):
    payload = {"email": "dupe@customer.example", "password": "Passw0rd!23", "full_name": "First"}
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/auth/register", json={**payload, "full_name": "Second"})
    assert second.status_code == 409


async def test_login_success(client, customer_user):
    resp = await client.post(
        "/auth/login", json={"email": customer_user.email, "password": "Passw0rd!23"}
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == customer_user.email


async def test_login_wrong_password_rejected(client, customer_user):
    resp = await client.post(
        "/auth/login", json={"email": customer_user.email, "password": "wrong-password"}
    )
    assert resp.status_code == 401


async def test_login_disabled_account_rejected(db, client):
    user = await make_user(db, email="disabled@customer.example", is_active=False)
    resp = await client.post("/auth/login", json={"email": user.email, "password": "Passw0rd!23"})
    assert resp.status_code == 403


async def test_me_requires_valid_token(client, customer_user):
    resp = await client.get("/auth/me", headers=auth_headers(customer_user))
    assert resp.status_code == 200
    assert resp.json()["id"] == str(customer_user.id)


async def test_me_rejects_garbage_token(client):
    resp = await client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower() or "expired" in resp.json()["detail"].lower()


async def test_me_rejects_missing_token(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401
