"""Platform-admin routes: bank onboarding, staff creation, deactivate/
reactivate (never a hard delete), and the 403 wall around all of it."""
from tests.conftest import auth_headers, make_bank, make_user


async def test_create_bank_also_creates_branch_manager_position(client, admin_headers):
    """create_bank's whole "how do you appoint someone to run a new bank"
    story rests on this starter position existing with full authority —
    regression-test the contract described in its own docstring."""
    resp = await client.post(
        "/admin/banks",
        json={"name": "New Bank", "code": "NB001", "contact_email": "ops@newbank.example"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    bank_id = resp.json()["id"]

    positions = await client.get(f"/admin/banks/{bank_id}/positions", headers=admin_headers)
    assert positions.status_code == 200
    body = positions.json()
    assert len(body) == 1
    assert body[0]["title"] == "Branch Manager"
    assert body[0]["max_approval_amount"] is None
    assert body[0]["can_manage_staff"] is True
    assert body[0]["can_manage_products"] is True


async def test_create_bank_duplicate_code_rejected(client, admin_headers, bank):
    resp = await client.post(
        "/admin/banks",
        json={"name": "Dupe", "code": bank.code, "contact_email": "a@b.example"},
        headers=admin_headers,
    )
    assert resp.status_code == 409


async def test_create_staff_for_bank(client, admin_headers, bank, manager_position):
    resp = await client.post(
        "/admin/staff",
        json={
            "email": "newstaff@testdomain.org",
            "password": "Passw0rd!23",
            "full_name": "New Staff",
            "bank_id": str(bank.id),
            "position_id": str(manager_position.id),
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["role"] == "staff"
    assert body["email"] == "newstaff@testdomain.org"


async def test_create_staff_rejects_position_from_another_bank(client, admin_headers, bank, manager_position, db):
    other_bank = await make_bank(db, name="Other Bank", code="OB001")
    resp = await client.post(
        "/admin/staff",
        json={
            "email": "mismatched@testdomain.org",
            "password": "Passw0rd!23",
            "full_name": "Mismatched",
            "bank_id": str(other_bank.id),
            "position_id": str(manager_position.id),
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400


async def test_deactivate_and_reactivate_user_is_soft(client, admin_headers, db):
    """Never a hard delete — deactivating just flips is_active, and the
    row (and its history) stays fully intact throughout."""
    user = await make_user(db, email="target@testdomain.org")

    deactivated = await client.post(f"/admin/users/{user.id}/deactivate", headers=admin_headers)
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    still_there = await client.get("/admin/users", headers=admin_headers)
    assert any(u["id"] == str(user.id) for u in still_there.json())

    reactivated = await client.post(f"/admin/users/{user.id}/reactivate", headers=admin_headers)
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True


async def test_admin_cannot_deactivate_own_account(client, admin_headers, admin_user):
    resp = await client.post(f"/admin/users/{admin_user.id}/deactivate", headers=admin_headers)
    assert resp.status_code == 400


async def test_no_hard_delete_route_exists(client, admin_headers, db):
    user = await make_user(db, email="nodelete@testdomain.org")
    resp = await client.delete(f"/admin/users/{user.id}", headers=admin_headers)
    assert resp.status_code in (404, 405)


async def test_non_admin_blocked_from_admin_routes(client, customer_headers, manager_headers):
    for headers in (customer_headers, manager_headers):
        resp = await client.get("/admin/users", headers=headers)
        assert resp.status_code == 403


async def test_admin_routes_require_auth(client):
    resp = await client.get("/admin/users")
    assert resp.status_code == 401


async def test_dashboard_counts(client, admin_headers, admin_user, bank):
    resp = await client.get("/admin/dashboard", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_users"] >= 1
    assert body["total_banks"] >= 1
