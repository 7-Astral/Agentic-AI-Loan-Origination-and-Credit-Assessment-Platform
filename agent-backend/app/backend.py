import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.agents.interaction.discovery import build_discovery_graph
from app.agents.interaction.graph import build_graph
from app.api.interview import router as interview_router
from app.core.config import get_settings
from app.services.core_banking import core_banking
from app.api.documents import router as documents_router
from app.core.db import Base, engine
from app.models.documents import Document, DocumentExtraction, VerificationResult 

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncPostgresSaver.from_conn_string(settings.langgraph_db_url) as checkpointer:
        await checkpointer.setup()
        app.state.discovery_graph = build_discovery_graph(checkpointer)
        app.state.interview_graph = build_graph(checkpointer)
        yield


app = FastAPI(title="AI Loan Origination Backend", version="0.2.0", lifespan=lifespan)

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
)

app.include_router(interview_router)
app.include_router(documents_router)

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