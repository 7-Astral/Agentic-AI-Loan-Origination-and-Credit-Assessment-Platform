from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    gemini_api_key: str = ""

    model_interaction: str = "gemini-3.5-flash-lite"
    model_document: str = "gemini-3.7-flash"
    model_assessment: str = "gemini-3.7-flash"
    model_decision: str = "gemini-3.7-flash"

    # Assessment configuration (document checklists, HEM/shading policy,
    # Five C's rules, interview slot schemas) — still served by mock_core_banking.
    core_banking_base_url: str = "http://127.0.0.1:9000"
    core_banking_api_key: str = "mock-key"
    core_banking_timeout: int = 15

    # Product catalog — served by the main platform's services/api, which is
    # the single source of truth for banks/loan_products/lending_policies.
    catalog_base_url: str = "http://127.0.0.1:8000"
    catalog_api_key: str = "dev-service-key-change-me"
    catalog_timeout: int = 15
    # Default bank whose catalog a chat session uses when the caller doesn't
    # specify one (StartRequest.bank_id). MVP simplification: one chat
    # deployment serves one bank's products, like a bank's own branded
    # assistant, rather than browsing a cross-bank marketplace.
    platform_bank_id: str = ""
    # Falls back to this stable bank code when platform_bank_id is blank —
    # avoids needing to hand-update a UUID every time the DB is reseeded.
    platform_bank_code: str = "FNB001"

    langgraph_db_url: str = "postgresql://postgres:admin@localhost:5432/loan_origination"
    app_database_url: str = "postgresql+asyncpg://postgres:admin@localhost:5432/loan_origination"    

    app_env: str = "local"
    log_level: str = "INFO"

    # Must match services/api's JWT settings exactly — a chat session
    # authenticates the customer using the same token the main platform
    # issued at login, not a login of its own.
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"

    def model_for(self, agent: str) -> str:
        mapping = {
            "interaction": self.model_interaction,
            "document": self.model_document,
            "assessment": self.model_assessment,
            "decision": self.model_decision,
        }
        if agent not in mapping:
            raise ValueError(
                f"Unknown agent '{agent}'. Expected one of {sorted(mapping)}"
            )
        return mapping[agent]


@lru_cache
def get_settings() -> Settings:
    return Settings()