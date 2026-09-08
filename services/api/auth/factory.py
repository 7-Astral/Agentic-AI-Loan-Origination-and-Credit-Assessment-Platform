from sqlalchemy.ext.asyncio import AsyncSession

from auth.providers import AuthProvider
from core.config import settings


def get_auth_provider(db: AsyncSession) -> AuthProvider:
    """Returns the active auth provider per AUTH_PROVIDER. Code should depend only on the
    AuthProvider protocol, obtained through this function — never import a specific
    provider class directly — so the provider can be swapped via config alone."""
    if settings.auth_provider == "local":
        from auth.local_provider import LocalAuthProvider

        return LocalAuthProvider(db)

    raise ValueError(f"Unknown auth provider: {settings.auth_provider}")
