"""Base class for SQLAlchemy models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


# Import all models here for Alembic autogenerate support
from app.models.agent_finding import AgentFinding  # noqa: E402, F401
from app.models.analysis import Analysis  # noqa: E402, F401
from app.models.artifact import Artifact  # noqa: E402, F401
from app.models.progress import AnalysisProgress  # noqa: E402, F401
from app.models.tutoring import TutoringMessage, TutoringSession  # noqa: E402, F401
