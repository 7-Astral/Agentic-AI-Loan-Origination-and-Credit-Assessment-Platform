"""Shared test fixtures for services/api.

Runs against a REAL Postgres database (not sqlite) — the models use
Postgres-specific types (UUID, JSONB, ARRAY, and the Fernet-encrypted
EncryptedString column), so a lighter substitute would test something other
than what actually runs in production. Point TEST_DATABASE_URL at a
throwaway database before running pytest (docker-compose already runs a
`db` service — see README/pytest.ini for the exact command); this file
creates and drops all tables in that database, so never point it at a real
one.

The DATABASE_URL env var is set *before* importing anything under app/, so
app.core.config.Settings() (instantiated at import time via
app.db.session.engine = create_async_engine(settings.database_url, ...))
picks up the test database from the start — no dependency-override dance
needed, the app's own engine already points at the right place.
"""
import os
import uuid

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/loan_origination_test",
)
# Fixed, known values for tests — never read real secrets from a dev/prod
# .env for this, since conftest.py sets DATABASE_URL unconditionally above
# and would otherwise run tests against mismatched app secrets.
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("SERVICE_API_KEY", "test-service-key")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.bank import Bank
from app.models.bank_position import BankPosition
from app.models.enums import BankStatus, UserRole
from app.models.lending_policy import LendingPolicy
from app.models.loan_product import LoanProduct, generate_product_code
from app.models.user import User


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _schema():
    """Create every table once for the whole test run, drop them at the end.
    Safe to re-run: starts by dropping anything left over from a previous
    interrupted run."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    """Truncate every table before each test so tests never see another
    test's data. Runs *before* the test (not just after) so a prior run
    that crashed mid-test without reaching teardown can't leave stale rows
    behind for the next one."""
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    yield


@pytest_asyncio.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role)
    return {"Authorization": f"Bearer {token}"}


async def make_user(
    db,
    *,
    email: str,
    password: str = "Passw0rd!23",
    full_name: str = "Test User",
    role: str = UserRole.CUSTOMER.value,
    bank_id=None,
    position_id=None,
    is_active: bool = True,
) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        bank_id=bank_id,
        position_id=position_id,
        is_active=is_active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def make_bank(db, *, name: str = "Test Bank", code: str = "TB001") -> Bank:
    bank = Bank(name=name, code=code, contact_email="ops@testbank.example", status=BankStatus.ACTIVE.value)
    db.add(bank)
    await db.commit()
    await db.refresh(bank)
    return bank


async def make_position(
    db,
    *,
    bank_id,
    title: str = "Branch Manager",
    rank: int = 1,
    max_approval_amount=None,
    can_manage_staff: bool = True,
    can_manage_products: bool = True,
) -> BankPosition:
    position = BankPosition(
        bank_id=bank_id,
        title=title,
        rank=rank,
        max_approval_amount=max_approval_amount,
        can_manage_staff=can_manage_staff,
        can_manage_products=can_manage_products,
    )
    db.add(position)
    await db.commit()
    await db.refresh(position)
    return position


async def make_product(
    db,
    *,
    bank_id,
    name: str = "Test Personal Loan",
    product_type: str = "personal",
    min_amount: float = 1000,
    max_amount: float = 50000,
    interest_rate_min: float = 5.0,
    interest_rate_max: float = 12.0,
    tenure_min_months: int = 6,
    tenure_max_months: int = 60,
    is_active: bool = True,
) -> LoanProduct:
    product_id = uuid.uuid4()
    product = LoanProduct(
        id=product_id,
        bank_id=bank_id,
        product_code=generate_product_code(product_type, product_id),
        product_type=product_type,
        name=name,
        min_amount=min_amount,
        max_amount=max_amount,
        interest_rate_min=interest_rate_min,
        interest_rate_max=interest_rate_max,
        tenure_min_months=tenure_min_months,
        tenure_max_months=tenure_max_months,
        is_active=is_active,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def make_policy(
    db,
    *,
    bank_id,
    product_id=None,
    auto_approval_max_amount: float = 10000,
    min_credit_score: int = 600,
    max_dti_ratio: float = 0.45,
    is_active: bool = True,
) -> LendingPolicy:
    policy = LendingPolicy(
        bank_id=bank_id,
        product_id=product_id,
        auto_approval_max_amount=auto_approval_max_amount,
        min_credit_score=min_credit_score,
        max_dti_ratio=max_dti_ratio,
        is_active=is_active,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


@pytest_asyncio.fixture
async def admin_user(db):
    return await make_user(db, email="admin@testdomain.org", role=UserRole.ADMIN.value)


@pytest.fixture
def admin_headers(admin_user):
    return auth_headers(admin_user)


@pytest_asyncio.fixture
async def bank(db):
    return await make_bank(db)


@pytest_asyncio.fixture
async def manager_position(db, bank):
    return await make_position(db, bank_id=bank.id, can_manage_staff=True, can_manage_products=True)


@pytest_asyncio.fixture
async def manager_user(db, bank, manager_position):
    return await make_user(
        db,
        email="manager@testdomain.org",
        role=UserRole.STAFF.value,
        bank_id=bank.id,
        position_id=manager_position.id,
    )


@pytest.fixture
def manager_headers(manager_user):
    return auth_headers(manager_user)


@pytest_asyncio.fixture
async def staff_officer_position(db, bank):
    """A lower rung than manager_position: no admin-style permissions, and a
    finite approval ceiling — used both for permission-gating tests (should
    be blocked from staff/product/policy management) and for escalation
    routing tests (an amount over the auto-approval threshold but within
    this position's ceiling should land here, not with the manager)."""
    return await make_position(
        db,
        bank_id=bank.id,
        title="Loan Officer",
        rank=2,
        max_approval_amount=20000,
        can_manage_staff=False,
        can_manage_products=False,
    )


@pytest_asyncio.fixture
async def staff_officer_user(db, bank, staff_officer_position):
    return await make_user(
        db,
        email="officer@testdomain.org",
        role=UserRole.STAFF.value,
        bank_id=bank.id,
        position_id=staff_officer_position.id,
    )


@pytest.fixture
def staff_officer_headers(staff_officer_user):
    return auth_headers(staff_officer_user)


@pytest_asyncio.fixture
async def customer_user(db):
    return await make_user(db, email="customer@testdomain.org", role=UserRole.CUSTOMER.value)


@pytest.fixture
def customer_headers(customer_user):
    return auth_headers(customer_user)
