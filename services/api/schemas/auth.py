import uuid

from pydantic import BaseModel

from models.enums import UserRole


class Credentials(BaseModel):
    email: str
    password: str


class AuthenticatedUser(BaseModel):
    """What `AuthProvider.authenticate()` returns on success, and the shape embedded in
    `LoginResponse`/`GET /auth/me`. Never carries `password_hash` or any other secret."""

    id: uuid.UUID
    email: str
    name: str
    role: UserRole
    bank_id: uuid.UUID | None


class UserClaims(BaseModel):
    """What `AuthProvider.get_user_claims()` returns after validating a token — the shape
    every route dependency and handler depends on. Route handlers must depend only on this,
    never on anything local-auth-specific, so swapping the provider later touches only
    auth/local_provider.py (or its replacement) and nothing else."""

    sub: str
    email: str
    name: str
    role: UserRole
    bank_id: uuid.UUID | None


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthenticatedUser


class RegisterRequest(BaseModel):
    """Customer self-registration only — deliberately has no `role` field. FastAPI/Pydantic
    silently drops any extra field a client sends (this codebase sets `extra="forbid"`
    nowhere), so a client POSTing `{"role": "admin", ...}` has it dropped before the handler
    ever runs; `routers/auth.py::register` additionally hardcodes `UserRole.customer`
    regardless, so there are two independent reasons this can't be bypassed."""

    name: str
    email: str
    password: str
    bank_id: uuid.UUID
