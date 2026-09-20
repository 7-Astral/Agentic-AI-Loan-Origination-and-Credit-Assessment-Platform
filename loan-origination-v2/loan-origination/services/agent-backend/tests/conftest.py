"""Shared test fixtures for services/agent-backend.

Runs against a REAL Postgres database for the operational read-model
(app.services.operational / app.models.application) — same reasoning as
services/api's suite: Postgres-specific types, and this is what actually
runs in production. Point TEST_APP_DATABASE_URL at a throwaway database
before running pytest; this file creates and drops the operational/identity
schemas in that database, so never point it at a real one.

The LangGraph control flow (discovery.py / graph.py) is tested with the
graphs' own default MemorySaver checkpointer instead of the real
AsyncPostgresSaver the app uses in production (see app.backend's lifespan)
— MemorySaver keeps state in the Python process for the life of one test's
graph object, which is exactly what a test needs and avoids depending on a
second, LangGraph-managed set of Postgres tables.

Two things that would otherwise need a real network call are always
stubbed: the Gemini LLM (app.core.llm.get_llm, bound separately into
discovery.py / extractor.py / questioner.py) and the catalog/assessment
HTTP client (the app.services.core_banking.core_banking singleton). See
the `fake_llm` and `fake_catalog` fixtures below.
"""
import os

os.environ["APP_DATABASE_URL"] = os.environ.get(
    "TEST_APP_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/agent_backend_test",
)
# Never read a real dev/prod .env for these — conftest.py sets
# APP_DATABASE_URL unconditionally above and would otherwise run against
# mismatched app secrets/keys.
os.environ["JWT_SECRET"] = "test-secret"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["CATALOG_API_KEY"] = "test-catalog-key"
os.environ["CORE_BANKING_API_KEY"] = "test-core-banking-key"
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")  # never actually called — see fake_llm
os.environ["PLATFORM_BANK_ID"] = ""

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import text

from app.agents.interaction.discovery import build_discovery_graph
from app.agents.interaction.graph import build_graph
from app.api.assessment import router as assessment_router
from app.api.decisions import router as decisions_router
from app.api.documents import router as documents_router
from app.api.interview import router as interview_router
from app.api.report import router as report_router
from app.core.config import get_settings
from app.core.db import Base, async_session, engine
from app.services.core_banking import core_banking
import app.models.application  # noqa: F401 registers Application/Message/... on Base.metadata
import app.models.documents  # noqa: F401 registers Document/... on Base.metadata
import app.models.identity  # noqa: F401 registers identity.users on Base.metadata

from fastapi import FastAPI


# ---------------------------------------------------------------- schema --

@pytest_asyncio.fixture(scope="session", autouse=True)
async def _schema():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS operational"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS identity"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    yield


@pytest_asyncio.fixture
async def db():
    async with async_session() as session:
        yield session


# ------------------------------------------------------------------ auth --

def customer_token(user_id: str | None = None, role: str = "customer") -> str:
    """A token shaped exactly like the one services/api's create_access_token
    issues (same claim names/secret contract — see app.core.identity)."""
    settings = get_settings()
    subject = user_id or str(uuid.uuid4())
    payload = {"sub": subject, "role": role, "exp": datetime.now(timezone.utc) + timedelta(minutes=60)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def auth_headers(user_id: str | None = None, role: str = "customer") -> dict[str, str]:
    return {"Authorization": f"Bearer {customer_token(user_id, role)}"}


# --------------------------------------------------------------- fake llm --

class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class FakeLLM:
    """A drop-in for ChatGoogleGenerativeAI.

    discovery.py's classify_type / classify_category / select nodes each
    call the LLM exactly once per turn (they never call interrupt()
    themselves), so those are served off a plain ordered queue.

    graph.py's ask_node is different: it calls the LLM *before* calling
    interrupt() inside the same node — and because a LangGraph node that
    calls interrupt() re-runs from the top of the function on every resume
    (see the comment in discovery.py's present_node), ask_node's LLM call
    fires TWICE per slot: once on the turn that pauses, and again
    (discarded) on the turn that resumes it, before ingest_node's own
    extract() call. A fixed ordered queue can't express that without
    duplicating every entry, and silently breaks the moment that doubling
    is ever fixed — so ask()/extract() calls are routed by slot id instead
    (found in the request payload) via `ask_texts` / `extract_responses`,
    keyed by slot id and reusable across repeated calls for the same slot.
    """

    def __init__(self):
        self.calls: list[list] = []
        self.discovery_queue: list[str] = []
        self.extract_responses: dict[str, dict] = {}
        self.ask_texts: dict[str, str] = {}
        self.default_ask_text = "Can you tell me more about that?"

    async def ainvoke(self, messages):
        self.calls.append(messages)
        system = messages[0].content
        human = messages[1].content

        if "You extract structured values" in system:
            payload = json.loads(human)
            fields = payload.get("fields_asked") or []
            slot_id = fields[0]["id"] if fields else None
            resp = self.extract_responses.get(slot_id, {"values": {}, "unclear": [], "notes": ""})
            return _FakeMessage(json.dumps(resp))

        if "You are a loan application assistant" in system:
            payload = json.loads(human)
            fields = payload.get("fields_to_ask") or []
            slot_id = fields[0]["id"] if fields else None
            return _FakeMessage(self.ask_texts.get(slot_id, self.default_ask_text))

        if not self.discovery_queue:
            raise AssertionError(f"FakeLLM discovery_queue exhausted; next call was: {messages}")
        return _FakeMessage(self.discovery_queue.pop(0))


@pytest.fixture
def fake_llm(monkeypatch):
    llm = FakeLLM()

    def _get_llm(agent: str):
        return llm

    monkeypatch.setattr("app.agents.interaction.discovery.get_llm", _get_llm)
    monkeypatch.setattr("app.agents.interaction.extractor.get_llm", _get_llm)
    monkeypatch.setattr("app.agents.interaction.questioner.get_llm", _get_llm)
    return llm


# ----------------------------------------------------------- fake catalog --

DEFAULT_TEST_BANK_ID = "11111111-1111-1111-1111-111111111111"

LOAN_TYPES = [
    {
        "code": "personal",
        "name": "Personal Loan",
        "description": "Unsecured loan for personal use.",
        "categories": [{"code": "general", "name": "General"}],
    },
    {
        "code": "home",
        "name": "Home Loan",
        "description": "Loan to buy or refinance residential property.",
        "categories": [
            {"code": "owner_occupied", "name": "Owner Occupied"},
            {"code": "investment", "name": "Investment"},
        ],
    },
]


def _product(code: str, name: str, **overrides) -> dict:
    base = {
        "product_code": code,
        "name": name,
        "interest_rate": 6.5,
        "comparison_rate": 6.9,
        "rate_type": "variable",
        "min_amount": 1000.0,
        "max_amount": 50000.0,
        "min_term_months": 6,
        "max_term_months": 60,
        "features": ["No early repayment fee"],
    }
    base.update(overrides)
    return base


DEFAULT_PRODUCTS = {
    ("personal", "general"): [_product("PERSONAL-AAAA1111", "Quick Personal Loan")],
    ("home", "owner_occupied"): [
        _product("HOME-BBBB2222", "Home Purchase Loan", min_amount=50000, max_amount=1000000),
        _product("HOME-CCCC3333", "Home Renovation Loan", min_amount=20000, max_amount=300000),
    ],
    ("home", "investment"): [_product("HOME-DDDD4444", "Investment Home Loan", min_amount=50000, max_amount=1000000)],
}

DEFAULT_SLOTS = [
    {
        "id": "loan_amount",
        "label": "Loan amount",
        "type": "currency",
        "phase": 1,
        "group": "loan_details",
        "required": True,
        "ask_hint": "How much would you like to borrow?",
        "validation": {"min": 1000, "max": 1000000},
    },
    {
        "id": "loan_term_months",
        "label": "Loan term (months)",
        "type": "number",
        "phase": 1,
        "group": "loan_details",
        "required": True,
        "ask_hint": "Over how many months?",
        "validation": {"min": 6, "max": 84},
    },
    {
        "id": "loan_purpose",
        "label": "Purpose",
        "type": "choice",
        "phase": 2,
        "group": "purpose",
        "required": True,
        "ask_hint": "What's this loan for?",
        "options": ["debt_consolidation", "car", "home_improvement", "other"],
    },
]


class FakeCatalog:
    """Stands in for the real app.services.core_banking.core_banking client
    (which hits services/api and mock_core_banking over HTTP) — configurable
    per test via .products / .loan_types / .slots, defaults above."""

    def __init__(self):
        self.loan_types = [dict(lt) for lt in LOAN_TYPES]
        self.products = {k: [dict(p) for p in v] for k, v in DEFAULT_PRODUCTS.items()}
        self.slots = [dict(s) for s in DEFAULT_SLOTS]
        self.bank_id = DEFAULT_TEST_BANK_ID
        self.submitted_applications: list[dict] = []

    async def list_loan_types(self, bank_id: str | None = None) -> list[dict]:
        return self.loan_types

    async def list_products(self, loan_type=None, category=None, bank_id=None) -> list[dict]:
        if loan_type and category:
            return self.products.get((loan_type, category), [])
        items = []
        for (lt, cat), prods in self.products.items():
            if loan_type and lt != loan_type:
                continue
            items.extend(prods)
        return items

    async def get_product_requirements(self, product_code: str, bank_id: str | None = None) -> dict:
        return {"product_code": product_code, "schema_version": "v1", "slots": self.slots}

    async def resolve_default_bank_id(self) -> str:
        return self.bank_id

    async def submit_application(self, **kwargs) -> dict:
        application_id = str(uuid.uuid4())
        self.submitted_applications.append({"application_id": application_id, **kwargs})
        return {"application_id": application_id, "status": "approved", "outcome": "auto_approved", "pending_position_title": None}


@pytest.fixture
def fake_catalog(monkeypatch):
    fc = FakeCatalog()
    monkeypatch.setattr(core_banking, "list_loan_types", fc.list_loan_types)
    monkeypatch.setattr(core_banking, "list_products", fc.list_products)
    monkeypatch.setattr(core_banking, "get_product_requirements", fc.get_product_requirements)
    monkeypatch.setattr(core_banking, "resolve_default_bank_id", fc.resolve_default_bank_id)
    monkeypatch.setattr(core_banking.catalog, "submit_application", fc.submit_application)
    return fc


# ------------------------------------------------------------------- app --

def make_test_app() -> FastAPI:
    """The same routers app.backend wires up, minus its lifespan (which
    needs a real AsyncPostgresSaver-backed Postgres connection) — graphs are
    attached directly below with their default in-memory checkpointer."""
    app = FastAPI()
    app.include_router(interview_router)
    app.include_router(documents_router)
    app.include_router(assessment_router)
    app.include_router(decisions_router)
    app.include_router(report_router)
    app.state.discovery_graph = build_discovery_graph()
    app.state.interview_graph = build_graph()
    return app


@pytest.fixture
def app():
    return make_test_app()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
