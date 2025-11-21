"""Base class for SQLAlchemy models."""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Import all models here for Alembic autogenerate support
from app.models.agent_finding import AgentFinding  # noqa: E402, F401
from app.models.analysis import Analysis  # noqa: E402, F401
from app.models.artifact import Artifact  # noqa: E402, F401
from app.models.progress import AnalysisProgress  # noqa: E402, F401
from app.models.tutoring import TutoringMessage, TutoringSession  # noqa: E402, F401
