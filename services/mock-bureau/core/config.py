from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolved relative to this file rather than left as a bare ".env" (which pydantic-settings
# would resolve against the process's current working directory) so it loads the right file
# regardless of which directory this service is started from.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Configuration for the mock credit bureau sandbox, sourced entirely from the
    environment. Client credentials default to fixed development values so the API service
    and this sandbox agree out of the box; override both together in `.env` if changed."""

    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    mock_bureau_client_id: str = "demo-client-id"
    mock_bureau_client_secret: str = "demo-client-secret"


settings = Settings()
