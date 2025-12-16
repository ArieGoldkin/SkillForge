"""Tutor domain schemas.

This package contains all Pydantic schemas for the tutor domain:
- api.py - API request/response schemas
- state.py - Workflow state schemas
- assessment.py - Assessment schemas
- syllabus.py - Syllabus schemas
"""

# Re-export all tutor schemas for convenience
from app.domains.tutor.schemas.api import (
    CreateSessionRequest,
    CreateSessionResponse,
    GetSessionResponse,
    SendMessageRequest,
    UpdateSessionRequest,
)
from app.domains.tutor.schemas.assessment import ReadinessAssessment
from app.domains.tutor.schemas.state import Message, TutorPhase
from app.domains.tutor.schemas.syllabus import Lesson, Section, Syllabus

__all__ = [
    # API
    "CreateSessionRequest",
    "CreateSessionResponse",
    "GetSessionResponse",
    "SendMessageRequest",
    "UpdateSessionRequest",
    # State
    "TutorPhase",
    "Message",
    # Assessment
    "ReadinessAssessment",
    # Syllabus
    "Syllabus",
    "Section",
    "Lesson",
]
