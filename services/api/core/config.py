from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolved relative to this file (services/api/core/config.py -> services/api/.env) rather
# than left as a bare ".env", which pydantic-settings would otherwise resolve against the
# process's current working directory — so this loads the right file (and, crucially, not
# the Docker-only repo-root .env) no matter which directory a command is run from.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Application configuration, sourced entirely from the environment."""

    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    database_url: str
    cors_origins: str

    llm_provider: str = "ollama"
    anthropic_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:latest"

    # Mock credit bureau sandbox (services/mock-bureau). Swap for a live bureau by pointing
    # mock_bureau_base_url at the real provider and updating the credentials — the OAuth2
    # client-credentials + Bearer-auth call shape in integration/credit_bureau.py is modelled
    # on how a real bureau sandbox behaves, so callers don't change.
    mock_bureau_base_url: str = "http://localhost:8001"
    mock_bureau_client_id: str = "demo-client-id"
    mock_bureau_client_secret: str = "demo-client-secret"
    mock_bureau_timeout_seconds: float = 5.0

    # ABN Lookup (Australian Business Register). Requires a free GUID registered with the
    # ABR web services (https://abr.business.gov.au/Tools/WebServices) — the collector
    # degrades to "unavailable" rather than failing when this is unset.
    abr_guid: str | None = None
    abr_timeout_seconds: float = 5.0

    # Auth. "local" is a documented dev-stage substitute for the target Entra ID (staff) /
    # Azure AD B2C (customers) architecture — see auth/providers.py and CLAUDE.md. No
    # default for jwt_secret: it must be set explicitly, the same way database_url is.
    auth_provider: str = "local"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 30

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
