from fastapi import FastAPI

from app.core.config import get_settings
from app.services.core_banking import core_banking

settings = get_settings()

app = FastAPI(title="AI Loan Origination Backend", version="0.1.0")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "env": settings.app_env,
        "llm_model": settings.llm_model,
        "core_banking": settings.core_banking_base_url,
    }


@app.get("/debug/loan-types")
async def debug_loan_types():
    return await core_banking.list_loan_types()


@app.get("/debug/products")
async def debug_products(loan_type: str | None = None, category: str | None = None):
    return await core_banking.list_products(loan_type, category)

