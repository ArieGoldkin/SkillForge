"""Base class for SQLAlchemy models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.

    Note: Model imports are NOT done here to avoid circular imports.
    Models import Base from this module, and if we import models here,
    we create a circular dependency.

    For Alembic autogenerate support, models are imported directly in
    alembic/env.py after Base is imported.
    """
