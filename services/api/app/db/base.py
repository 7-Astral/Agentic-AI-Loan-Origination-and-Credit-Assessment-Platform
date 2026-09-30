from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base — all models in app/models/ inherit from this."""

    pass


# Imported at the bottom (not the top) to avoid a circular import, since every
# model file does `from app.db.base import Base`. This import is what makes
# Base.metadata aware of all tables for Alembic autogenerate.
from app.models import *  # noqa: E402, F401, F403
