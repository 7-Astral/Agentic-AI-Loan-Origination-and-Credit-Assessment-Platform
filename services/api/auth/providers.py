from typing import Protocol

from schemas.auth import AuthenticatedUser, Credentials, UserClaims


class AuthProvider(Protocol):
    """Vendor-agnostic interface route handlers and the frontend depend on. Swap the
    provider by swapping the implementation returned from `auth.factory.get_auth_provider`
    — no other code should import a specific provider directly. `LocalAuthProvider` is a
    documented dev-stage substitute for the target Entra ID (staff) / Azure AD B2C
    (customers) architecture — see CLAUDE.md."""

    async def authenticate(self, credentials: Credentials) -> AuthenticatedUser | None:
        """Verifies credentials and returns the authenticated user, or None on failure —
        never raises for a wrong password or unknown email, those are legitimate outcomes."""
        ...

    async def get_user_claims(self, token: str) -> UserClaims | None:
        """Validates a bearer token and returns the claims it carries, or None if the token
        is missing, malformed, expired, or otherwise invalid."""
        ...
