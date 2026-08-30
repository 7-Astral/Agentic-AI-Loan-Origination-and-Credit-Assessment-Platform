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

    core_banking_base_url: str = "http://127.0.0.1:9000"
    core_banking_api_key: str = "mock-key"
    core_banking_timeout: int = 15

    langgraph_db_url: str = "postgresql://postgres:admin@localhost:5432/loan_origination"
    app_database_url: str = "postgresql+asyncpg://postgres:admin@localhost:5432/loan_origination"    

    app_env: str = "local"
    log_level: str = "INFO"

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