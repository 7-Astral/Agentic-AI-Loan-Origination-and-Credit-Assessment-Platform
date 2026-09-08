from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class CustomerProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employment_status: str | None = None
    income: Decimal | None = None
    expenses: Decimal | None = None
    assets: dict[str, Any] = {}
    liabilities: dict[str, Any] = {}


class CustomerProfileUpdate(BaseModel):
    """All fields optional — PATCH semantics. Only fields explicitly present in the request
    body are applied (see routers/users.py, `exclude_unset=True`)."""

    employment_status: str | None = None
    income: Decimal | None = None
    expenses: Decimal | None = None
    assets: dict[str, Any] | None = None
    liabilities: dict[str, Any] | None = None
