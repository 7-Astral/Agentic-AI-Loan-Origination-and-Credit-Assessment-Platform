"""Bank-staff lending-policy management — CRUD, soft deactivate/reactivate,
and is_active filtering feeding into route_loan_decision's policy lookup."""
from tests.conftest import make_policy, make_product


async def test_create_policy(client, manager_headers, bank):
    resp = await client.post(
        "/bank/lending-policies",
        json={"auto_approval_max_amount": 15000, "min_credit_score": 650, "max_dti_ratio": 0.4},
        headers=manager_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["auto_approval_max_amount"] == 15000.0
    assert body["is_active"] is True


async def test_create_policy_rejects_product_from_another_bank(client, manager_headers, db):
    from tests.conftest import make_bank

    other_bank = await make_bank(db, name="Other Bank", code="OB003")
    other_product = await make_product(db, bank_id=other_bank.id)

    resp = await client.post(
        "/bank/lending-policies",
        json={
            "product_id": str(other_product.id),
            "auto_approval_max_amount": 5000,
            "min_credit_score": 600,
            "max_dti_ratio": 0.5,
        },
        headers=manager_headers,
    )
    assert resp.status_code == 400


async def test_update_policy_partial(client, manager_headers, bank, db):
    policy = await make_policy(db, bank_id=bank.id, auto_approval_max_amount=10000)

    resp = await client.patch(
        f"/bank/lending-policies/{policy.id}",
        json={"auto_approval_max_amount": 25000},
        headers=manager_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["auto_approval_max_amount"] == 25000.0
    assert body["min_credit_score"] == policy.min_credit_score


async def test_deactivate_policy_removes_it_from_bank_listing_filter(client, manager_headers, bank, db):
    """The route itself returns every policy regardless of is_active (staff
    should be able to see inactive ones), but the flag must actually flip —
    _applicable_policy in lending_logic is what excludes inactive policies
    from governing new decisions (covered end-to-end in test_lending_logic)."""
    policy = await make_policy(db, bank_id=bank.id)

    resp = await client.post(f"/bank/lending-policies/{policy.id}/deactivate", headers=manager_headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    listing = await client.get("/bank/lending-policies", headers=manager_headers)
    entry = next(p for p in listing.json() if p["id"] == str(policy.id))
    assert entry["is_active"] is False

    reactivated = await client.post(f"/bank/lending-policies/{policy.id}/reactivate", headers=manager_headers)
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True


async def test_policy_management_requires_can_manage_products(client, staff_officer_headers):
    resp = await client.post(
        "/bank/lending-policies",
        json={"auto_approval_max_amount": 5000, "min_credit_score": 600, "max_dti_ratio": 0.5},
        headers=staff_officer_headers,
    )
    assert resp.status_code == 403
