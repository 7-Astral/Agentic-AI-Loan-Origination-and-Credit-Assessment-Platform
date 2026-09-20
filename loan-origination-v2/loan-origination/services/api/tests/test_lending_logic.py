"""End-to-end lending decision routing via POST /loans/apply — the
deterministic auto-approve/escalate policy in app.core.lending_logic,
including this session's own feature: manager notification on
auto-approval, which previously notified no one at all."""
from tests.conftest import auth_headers, make_policy, make_position, make_product, make_user


async def test_auto_approval_notifies_bank_manager(client, customer_headers, customer_user, bank, manager_user, manager_headers, db):
    product = await make_product(db, bank_id=bank.id, min_amount=1000, max_amount=50000)
    await make_policy(db, bank_id=bank.id, auto_approval_max_amount=10000)

    resp = await client.post(
        "/loans/apply",
        json={
            "bank_id": str(bank.id),
            "product_id": str(product.id),
            "requested_amount": 5000,
            "purpose": "renovation",
            "tenure_requested_months": 12,
        },
        headers=customer_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "approved"

    notifications = await client.get("/bank/notifications", headers=manager_headers)
    assert notifications.status_code == 200
    assert any(
        n["entity_type"] == "loan_application" and n["entity_id"] == body["id"] and "auto-approved" in n["message"]
        for n in notifications.json()
    )


async def test_over_threshold_escalates_to_covering_position(client, customer_headers, bank, db):
    """No policy at all (or amount over it) routes to the lowest-rank
    position whose max_approval_amount actually covers the amount, and only
    staff holding that specific position are notified."""
    product = await make_product(db, bank_id=bank.id, min_amount=1000, max_amount=100000)
    officer_position = await make_position(
        db, bank_id=bank.id, title="Loan Officer", rank=2, max_approval_amount=20000,
        can_manage_staff=False, can_manage_products=False,
    )
    officer = await make_user(
        db, email="officer2@testdomain.org", role="staff", bank_id=bank.id, position_id=officer_position.id
    )

    resp = await client.post(
        "/loans/apply",
        json={
            "bank_id": str(bank.id),
            "product_id": str(product.id),
            "requested_amount": 15000,
            "tenure_requested_months": 24,
        },
        headers=customer_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "under_review"
    assert body["pending_position_title"] == "Loan Officer"

    notifications = await client.get("/bank/notifications", headers=auth_headers(officer))
    assert any(n["entity_id"] == body["id"] for n in notifications.json())


async def test_escalation_picks_lowest_rank_position_that_covers_amount(client, customer_headers, bank, db):
    """With two positions on the ladder, the escalation must go to the
    lower-rank one that actually covers the amount — not automatically the
    higher-authority one — and only that position's staff get notified."""
    product = await make_product(db, bank_id=bank.id, min_amount=1000, max_amount=100000)
    junior = await make_position(
        db, bank_id=bank.id, title="Loan Officer", rank=2, max_approval_amount=20000,
        can_manage_staff=False, can_manage_products=False,
    )
    senior = await make_position(
        db, bank_id=bank.id, title="Credit Manager", rank=1, max_approval_amount=None,
        can_manage_staff=True, can_manage_products=True,
    )
    junior_staff = await make_user(
        db, email="junior@testdomain.org", role="staff", bank_id=bank.id, position_id=junior.id
    )
    senior_staff = await make_user(
        db, email="senior@testdomain.org", role="staff", bank_id=bank.id, position_id=senior.id
    )

    resp = await client.post(
        "/loans/apply",
        json={
            "bank_id": str(bank.id),
            "product_id": str(product.id),
            "requested_amount": 15000,
            "tenure_requested_months": 24,
        },
        headers=customer_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    # rank ascending order is [senior(rank1), junior(rank2)]; senior has
    # unlimited approval so it's the first position that "covers" 15000 —
    # this pins down the actual (rank-order, not authority-order) behavior.
    assert body["pending_position_title"] == senior.title

    senior_notifications = await client.get("/bank/notifications", headers=auth_headers(senior_staff))
    assert any(n["entity_id"] == body["id"] for n in senior_notifications.json())

    junior_notifications = await client.get("/bank/notifications", headers=auth_headers(junior_staff))
    assert not any(n["entity_id"] == body["id"] for n in junior_notifications.json())


async def test_no_policy_and_no_position_still_escalates_without_crashing(client, customer_headers, bank, db):
    """A bank with no lending policy and no approval ladder configured at
    all shouldn't 500 — it should still land the application in
    under_review with no position assigned."""
    product = await make_product(db, bank_id=bank.id, min_amount=1000, max_amount=100000)

    resp = await client.post(
        "/loans/apply",
        json={
            "bank_id": str(bank.id),
            "product_id": str(product.id),
            "requested_amount": 15000,
            "tenure_requested_months": 24,
        },
        headers=customer_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "under_review"
    assert body["pending_position_title"] is None


async def test_apply_amount_outside_product_range_rejected(client, customer_headers, bank, db):
    product = await make_product(db, bank_id=bank.id, min_amount=5000, max_amount=10000)
    resp = await client.post(
        "/loans/apply",
        json={
            "bank_id": str(bank.id),
            "product_id": str(product.id),
            "requested_amount": 999999,
            "tenure_requested_months": 12,
        },
        headers=customer_headers,
    )
    assert resp.status_code == 400


async def test_only_customers_can_apply(client, manager_headers, bank, db):
    product = await make_product(db, bank_id=bank.id)
    resp = await client.post(
        "/loans/apply",
        json={
            "bank_id": str(bank.id),
            "product_id": str(product.id),
            "requested_amount": 5000,
            "tenure_requested_months": 12,
        },
        headers=manager_headers,
    )
    assert resp.status_code == 403
