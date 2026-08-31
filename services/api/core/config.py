from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced entirely from the environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    cors_origins: str

    llm_provider: str = "ollama"
    anthropic_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:latest"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
