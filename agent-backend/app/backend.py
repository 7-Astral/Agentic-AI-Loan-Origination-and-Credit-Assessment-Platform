import asyncio
import re
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from starlette.routing import Match

from app.agents.interaction.discovery import build_discovery_graph
from app.agents.interaction.graph import build_graph
from app.api.interview import router as interview_router
from app.core import injection_guard, observability, privacy
from app.core.config import get_settings
from app.services.core_banking import core_banking
from app.api.documents import router as documents_router
from app.api.decisions import router as decisions_router
from app.api.report import router as report_router
from app.api.info_requests import router as info_requests_router
from app.models.documents import Document, DocumentExtraction, VerificationResult
from app.models.application import Application, ApplicationSlot, AssessmentResult, Decision, Message
from app.models.identity import User
from app.api.assessment import router as assessment_router
from app.api.applications_admin import router as applications_admin_router
from app.api.playground import router as playground_router
from app.api.playground_documents import router as playground_documents_router
from app.api.policy import router as policy_router
from app.models.policy import PolicyChunk

settings = get_settings()

SESSION_PATH = re.compile(
    r"^/api/v1/applications/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.IGNORECASE
)
UNTRACED_PATHS = ("/health", "/debug", "/docs", "/redoc", "/openapi.json")
TRACED_GET_SUFFIXES = ("/assessment", "/report", "/report/narrative", "/chat-report")


async def _warm_up_guards() -> None:
    if settings.pii_masking_enabled:
        await asyncio.to_thread(privacy.analyzer)
    if settings.prompt_guard_enabled:
        await asyncio.to_thread(injection_guard.warm_up)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _warm_up_guards()
    async with AsyncPostgresSaver.from_conn_string(settings.langgraph_db_url) as checkpointer:
        await checkpointer.setup()
        app.state.discovery_graph = build_discovery_graph(checkpointer)
        app.state.interview_graph = build_graph(checkpointer)
        try:
            yield
        finally:
            observability.flush()


app = FastAPI(title="AI Loan Origination Backend", version="0.2.0", lifespan=lifespan)


def _match_template(routes, scope) -> str | None:
    for route in routes:
        nested = getattr(route, "original_router", None)
        if nested is not None:
            found = _match_template(nested.routes, scope)
            if found:
                return found
            continue
        if getattr(route, "path", None) and route.matches(scope)[0] == Match.FULL:
            return route.path
    return None


def _route_template(request: Request) -> str:
    return _match_template(request.app.router.routes, request.scope) or request.url.path


def _viewer(request: Request) -> tuple[str | None, str | None]:
    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("bearer "):
        return None, "service" if request.headers.get("x-api-key") else "anonymous"
    try:
        payload = jwt.decode(header.split(" ", 1)[1].strip(), settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None, "invalid-token"
    return payload.get("sub"), payload.get("role")


def _should_trace(request: Request, template: str) -> bool:
    if request.method == "OPTIONS" or request.url.path.startswith(UNTRACED_PATHS):
        return False
    if request.method == "GET":
        return template.endswith(TRACED_GET_SUFFIXES)
    return True


@app.middleware("http")
async def trace_request(request: Request, call_next):
    match = SESSION_PATH.match(request.url.path)
    session = match.group(1).lower() if match else None
    token = observability.session_id.set(session)
    try:
        template = _route_template(request)
        if observability.client() is None or not _should_trace(request, template):
            return await call_next(request)

        user_id, role = _viewer(request)
        name = f"{request.method} {template.removeprefix('/api/v1')}"
        with observability.trace(
            name,
            input={"method": request.method, "path": request.url.path, "query": dict(request.query_params)},
            user_id=user_id,
            session=session,
            tags=["api", f"role:{role}", f"route:{template.removeprefix('/api/v1')}"],
            metadata={"route": template, "role": role, "app_version": app.version},
        ) as root:
            try:
                response = await call_next(request)
            except Exception as exc:
                root.update(level="ERROR", status_message=f"{type(exc).__name__}: {str(exc)[:500]}")
                raise
            root.update(
                output={"status_code": response.status_code},
                level="ERROR" if response.status_code >= 500 else "WARNING" if response.status_code >= 400 else None,
            )
            trace_id = observability.current_trace_id()
            if trace_id:
                response.headers["X-Trace-Id"] = trace_id
            return response
    finally:
        observability.session_id.reset(token)


@app.exception_handler(injection_guard.InjectionBlocked)
async def injection_blocked(request: Request, exc: injection_guard.InjectionBlocked):
    return JSONResponse(status_code=422, content={"detail": injection_guard.BLOCKED_MESSAGE})

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-Id"],
)

app.include_router(interview_router)
app.include_router(documents_router)
app.include_router(assessment_router)
app.include_router(applications_admin_router)
app.include_router(decisions_router)
app.include_router(playground_router)
app.include_router(playground_documents_router)
app.include_router(report_router)
app.include_router(info_requests_router)
app.include_router(policy_router)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "env": settings.app_env,
        "core_banking": settings.core_banking_base_url,
    }


@app.get("/debug/products")
async def debug_products(loan_type: str | None = None, category: str | None = None):
    return await core_banking.list_products(loan_type, category)