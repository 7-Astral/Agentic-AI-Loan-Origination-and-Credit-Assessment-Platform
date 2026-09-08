from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from routers import applications, auth, banks, conversations, health, risk_assessment, users

app = FastAPI(title="Agentic AI Loan Origination API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(banks.router)
app.include_router(conversations.router)
app.include_router(risk_assessment.router)
app.include_router(auth.router)
app.include_router(applications.router)
app.include_router(users.router)
