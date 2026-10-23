"""Bank-staff team management — create/update/deactivate/reactivate other
staff, self-protection on deactivate, and confirming there's still no
hard-delete route for staff either."""
from tests.conftest import make_position, make_user


async def test_create_staff_member(client, manager_headers, bank, manager_position):
    resp = await client.post(
        "/bank/staff",
        json={
            "email": "teammate@testdomain.org",
            "password": "Passw0rd!23",
            "full_name": "Team Mate",
            "position_id": str(manager_position.id),
        },
        headers=manager_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["role"] == "staff"


async def test_create_staff_rejects_position_from_another_bank(client, manager_headers, db):
    from tests.conftest import make_bank

    other_bank = await make_bank(db, name="Other Bank", code="OB004")
    other_position = await make_position(db, bank_id=other_bank.id)

    resp = await client.post(
        "/bank/staff",
        json={
            "email": "cross@testdomain.org",
            "password": "Passw0rd!23",
            "full_name": "Cross Bank",
            "position_id": str(other_position.id),
        },
        headers=manager_headers,
    )
    assert resp.status_code == 400


async def test_update_staff_partial_fields(client, manager_headers, bank, manager_position, db):
    staff = await make_user(
        db, email="editme@testdomain.org", role="staff", bank_id=bank.id, position_id=manager_position.id
    )
    resp = await client.patch(
        f"/bank/staff/{staff.id}",
        json={"full_name": "Edited Name"},
        headers=manager_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Edited Name"


async def test_deactivate_and_reactivate_staff_is_soft(client, manager_headers, bank, manager_position, db):
    staff = await make_user(
        db, email="softdelete@testdomain.org", role="staff", bank_id=bank.id, position_id=manager_position.id
    )
    deactivated = await client.post(f"/bank/staff/{staff.id}/deactivate", headers=manager_headers)
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    reactivated = await client.post(f"/bank/staff/{staff.id}/reactivate", headers=manager_headers)
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True


async def test_staff_cannot_deactivate_self(client, manager_headers, manager_user):
    resp = await client.post(f"/bank/staff/{manager_user.id}/deactivate", headers=manager_headers)
    assert resp.status_code == 400


async def test_no_hard_delete_route_for_staff(client, manager_headers, bank, manager_position, db):
    staff = await make_user(
        db, email="nodelete2@testdomain.org", role="staff", bank_id=bank.id, position_id=manager_position.id
    )
    resp = await client.delete(f"/bank/staff/{staff.id}", headers=manager_headers)
    assert resp.status_code in (404, 405)


async def test_staff_management_requires_can_manage_staff(client, staff_officer_headers, manager_position):
    resp = await client.post(
        "/bank/staff",
        json={
            "email": "blocked@testdomain.org",
            "password": "Passw0rd!23",
            "full_name": "Blocked",
            "position_id": str(manager_position.id),
        },
        headers=staff_officer_headers,
    )
    assert resp.status_code == 403


async def test_staff_routes_scoped_to_own_bank(client, manager_headers, db):
    """A manager can't edit staff belonging to a different bank."""
    from tests.conftest import make_bank

    other_bank = await make_bank(db, name="Other Bank", code="OB005")
    other_position = await make_position(db, bank_id=other_bank.id)
    other_staff = await make_user(
        db, email="other-staff@testdomain.org", role="staff", bank_id=other_bank.id, position_id=other_position.id
    )

    resp = await client.patch(
        f"/bank/staff/{other_staff.id}",
        json={"full_name": "Hijacked"},
        headers=manager_headers,
    )
    assert resp.status_code == 404
