import uuid
from decimal import Decimal

from fastapi.testclient import TestClient

from core.database import AsyncSessionLocal, engine
from main import app
from models.bank import Bank
from models.enums import BankStatus, LoanType
from models.loan_product import LoanProduct


async def _create_bank_with_product(slug: str) -> None:
    async with AsyncSessionLocal() as db:
        bank = Bank(
            name="API Test Bank",
            slug=slug,
            branding={"primary_color": "#123456", "logo_url": "/logos/test.svg"},
            status=BankStatus.active,
        )
        db.add(bank)
        await db.flush()
        db.add(
            LoanProduct(
                bank_id=bank.id,
                name="Test Personal Loan",
                type=LoanType.personal,
                interest_rate=Decimal("9.99"),
                min_amount=Decimal("1000"),
                max_amount=Decimal("10000"),
                min_term_months=12,
                max_term_months=36,
                eligibility_rules={},
                active=True,
            )
        )
        await db.commit()


async def test_get_bank_returns_branding_and_products() -> None:
    slug = f"api-test-{uuid.uuid4().hex[:8]}"
    await _create_bank_with_product(slug)

    # TestClient drives the ASGI app on its own event loop (a background thread's portal).
    # Dispose the pool first so the request opens fresh, loop-correct connections rather
    # than reusing ones checked out under this test's own event loop above.
    await engine.dispose()

    with TestClient(app) as client:
        response = client.get(f"/banks/{slug}")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Test Bank"
    assert data["branding"]["primary_color"] == "#123456"
    assert len(data["products"]) == 1
    assert data["products"][0]["type"] == "personal"


async def test_get_bank_404_for_unknown_slug() -> None:
    with TestClient(app) as client:
        response = client.get("/banks/does-not-exist-slug")

    assert response.status_code == 404
