"""Core-banking-style catalog contract (/api/v1/...) consumed by the chat
agent — X-API-Key auth, and the exact contract the "Home Loan H" bug from
earlier this project depended on: two products sharing the same
product_type must both appear together in a listing."""
from app.core.config import settings
from tests.conftest import make_product

API_KEY_HEADERS = {"X-API-Key": settings.service_api_key}


async def test_missing_api_key_rejected(client, bank):
    resp = await client.get(f"/api/v1/products?bank_id={bank.id}")
    assert resp.status_code == 401


async def test_wrong_api_key_rejected(client, bank):
    resp = await client.get(f"/api/v1/products?bank_id={bank.id}", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


async def test_two_products_same_product_type_both_listed(client, bank, db):
    """Regression test for the earlier bug where a product with the wrong
    product_type stored ("Home Loan H" stored as personal instead of home)
    silently vanished from its expected loan-type grouping — this pins down
    that two ACTUAL same-type products both come back together."""
    await make_product(db, bank_id=bank.id, name="Home Purchase Loan", product_type="home")
    await make_product(db, bank_id=bank.id, name="Home Renovation Loan", product_type="home")

    resp = await client.get(f"/api/v1/products?bank_id={bank.id}&loan_type=home", headers=API_KEY_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2
    names = {p["name"] for p in body["products"]}
    assert names == {"Home Purchase Loan", "Home Renovation Loan"}


async def test_inactive_products_excluded_from_catalog(client, bank, db):
    await make_product(db, bank_id=bank.id, name="Retired Product", is_active=False)
    resp = await client.get(f"/api/v1/products?bank_id={bank.id}", headers=API_KEY_HEADERS)
    assert resp.status_code == 200
    assert not any(p["name"] == "Retired Product" for p in resp.json()["products"])


async def test_get_product_by_code(client, bank, db):
    product = await make_product(db, bank_id=bank.id, name="Findable Product")
    resp = await client.get(
        f"/api/v1/products/{product.product_code}?bank_id={bank.id}", headers=API_KEY_HEADERS
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Findable Product"


async def test_get_bank_by_code(client, bank):
    resp = await client.get(f"/api/v1/banks/by-code/{bank.code}", headers=API_KEY_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["id"] == str(bank.id)


async def test_submit_application_routes_through_same_lending_logic(client, bank, db, manager_user, manager_headers):
    from tests.conftest import make_policy, make_user

    product = await make_product(db, bank_id=bank.id, min_amount=1000, max_amount=50000)
    await make_policy(db, bank_id=bank.id, auto_approval_max_amount=10000)
    applicant = await make_user(db, email="chatcustomer@testdomain.org", role="customer")

    resp = await client.post(
        "/api/v1/applications",
        json={
            "bank_id": str(bank.id),
            "product_code": product.product_code,
            "applicant_id": str(applicant.id),
            "requested_amount": 5000,
            "tenure_requested_months": 12,
            "external_reference": "chat-session-123",
        },
        headers=API_KEY_HEADERS,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["outcome"] == "auto_approved"
    assert body["status"] == "approved"

    # Same manager-notification path as the plain apply-form flow.
    notifications = await client.get("/bank/notifications", headers=manager_headers)
    assert any(n["entity_id"] == body["application_id"] for n in notifications.json())
