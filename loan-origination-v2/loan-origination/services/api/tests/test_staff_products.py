"""Bank-staff product management — create (regression test for the
product_code NOT NULL bug fixed earlier), partial update, soft
deactivate/reactivate, and can_manage_products gating."""
from tests.conftest import make_product


async def test_create_product_sets_product_code(client, manager_headers, bank):
    """product_code is NOT NULL + unique at the DB level and must be set on
    the INSERT itself (see generate_product_code) — this is the exact bug
    that broke product creation earlier this project."""
    resp = await client.post(
        "/bank/loan-products",
        json={
            "product_type": "personal",
            "name": "Quick Cash",
            "min_amount": 1000,
            "max_amount": 20000,
            "interest_rate_min": 6.5,
            "interest_rate_max": 14.0,
            "tenure_min_months": 6,
            "tenure_max_months": 36,
        },
        headers=manager_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["product_code"]
    assert body["product_code"].startswith("PERSONAL-")
    assert body["bank_id"] == str(bank.id)


async def test_update_product_partial_fields_only(client, manager_headers, bank, db):
    product = await make_product(db, bank_id=bank.id, name="Original Name", max_amount=10000)

    resp = await client.patch(
        f"/bank/loan-products/{product.id}",
        json={"name": "Renamed"},
        headers=manager_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Renamed"
    # Untouched fields must survive the partial update unchanged.
    assert body["max_amount"] == 10000.0


async def test_deactivate_product_is_soft_and_hides_from_active_listing(client, manager_headers, bank, db):
    product = await make_product(db, bank_id=bank.id)

    deactivated = await client.post(f"/bank/loan-products/{product.id}/deactivate", headers=manager_headers)
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    # Staff's own listing still shows it (soft delete, not gone)...
    staff_list = await client.get("/bank/loan-products", headers=manager_headers)
    assert any(p["id"] == str(product.id) for p in staff_list.json())

    # ...but the public/customer-facing active listing no longer does.
    public_list = await client.get("/loans/products")
    assert not any(p["id"] == str(product.id) for p in public_list.json())

    reactivated = await client.post(f"/bank/loan-products/{product.id}/reactivate", headers=manager_headers)
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True


async def test_product_management_requires_can_manage_products(client, staff_officer_headers):
    """A staff member whose position lacks can_manage_products is blocked,
    even though they're legitimately bank staff."""
    resp = await client.post(
        "/bank/loan-products",
        json={
            "product_type": "personal",
            "name": "Blocked Product",
            "min_amount": 1000,
            "max_amount": 5000,
            "interest_rate_min": 5,
            "interest_rate_max": 10,
            "tenure_min_months": 6,
            "tenure_max_months": 24,
        },
        headers=staff_officer_headers,
    )
    assert resp.status_code == 403


async def test_product_routes_scoped_to_own_bank(client, manager_headers, db):
    """A manager at bank A can't touch a product belonging to bank B."""
    from tests.conftest import make_bank

    other_bank = await make_bank(db, name="Other Bank", code="OB002")
    other_product = await make_product(db, bank_id=other_bank.id)

    resp = await client.patch(
        f"/bank/loan-products/{other_product.id}",
        json={"name": "Hijacked"},
        headers=manager_headers,
    )
    assert resp.status_code == 404
