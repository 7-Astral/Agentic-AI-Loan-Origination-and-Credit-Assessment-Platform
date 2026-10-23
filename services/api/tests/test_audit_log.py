"""Audit logging: entries carry a bank_id, entity_label resolves to a human
name (not a raw UUID) via resolve_entity_labels, and the bank-scoped audit
log route is gated to managers only (require_bank_manager) — the exact
"can I see only name/number, not raw sensitive data" contract from earlier
in this project."""
from tests.conftest import make_product


async def test_staff_created_audit_log_has_bank_id_and_resolves_label(client, manager_headers, manager_position, bank):
    resp = await client.post(
        "/bank/staff",
        json={
            "email": "audited@testdomain.org",
            "password": "Passw0rd!23",
            "full_name": "Audited Person",
            "position_id": str(manager_position.id),
        },
        headers=manager_headers,
    )
    assert resp.status_code == 201
    new_staff_id = resp.json()["id"]

    logs = await client.get("/bank/audit-logs", headers=manager_headers)
    assert logs.status_code == 200
    entry = next(e for e in logs.json() if e["entity_type"] == "user" and e["entity_id"] == new_staff_id)
    assert entry["entity_label"] == "Audited Person"
    assert entry["action"] == "staff_created"


async def test_product_audit_log_resolves_to_product_name(client, manager_headers, bank, db):
    product = await make_product(db, bank_id=bank.id, name="Special Product")
    await client.post(
        f"/bank/loan-products/{product.id}/deactivate",
        headers=manager_headers,
    )

    logs = await client.get("/bank/audit-logs", headers=manager_headers)
    entry = next(
        e for e in logs.json() if e["entity_type"] == "loan_product" and e["entity_id"] == str(product.id)
    )
    assert entry["entity_label"] == "Special Product"


async def test_bank_audit_log_requires_manager_not_just_any_permission(client, staff_officer_headers):
    """require_bank_manager needs BOTH can_manage_staff and
    can_manage_products — a position with neither (or only one) is
    blocked, unlike the Team/Products/Policies routes which only need one."""
    resp = await client.get("/bank/audit-logs", headers=staff_officer_headers)
    assert resp.status_code == 403


async def test_bank_audit_log_scoped_to_own_bank_only(client, manager_headers, bank, db):
    from tests.conftest import make_bank, make_position, make_user, auth_headers

    other_bank = await make_bank(db, name="Other Bank", code="OB006")
    other_manager_position = await make_position(db, bank_id=other_bank.id)
    other_manager = await make_user(
        db,
        email="othermanager@testdomain.org",
        role="staff",
        bank_id=other_bank.id,
        position_id=other_manager_position.id,
    )
    other_product = await make_product(db, bank_id=other_bank.id, name="Other Bank Product")
    await client.post(f"/bank/loan-products/{other_product.id}/deactivate", headers=auth_headers(other_manager))

    logs = await client.get("/bank/audit-logs", headers=manager_headers)
    assert not any(e["entity_id"] == str(other_product.id) for e in logs.json())


async def test_admin_audit_log_sees_across_all_banks(client, admin_headers, manager_headers, manager_position, bank):
    await client.post(
        "/bank/staff",
        json={
            "email": "seenbyadmin@testdomain.org",
            "password": "Passw0rd!23",
            "full_name": "Seen By Admin",
            "position_id": str(manager_position.id),
        },
        headers=manager_headers,
    )
    logs = await client.get("/admin/audit-logs", headers=admin_headers)
    assert logs.status_code == 200
    assert any(e["action"] == "staff_created" for e in logs.json())
