"""Tutor API endpoints.

Split into modules for better organization and SOLID principles.
"""

from fastapi import APIRouter

from app.api.v1.tutor import messages, sessions, streaming, topics

router = APIRouter(tags=["tutor"])

# Include sub-routers
router.include_router(topics.router)
router.include_router(sessions.router)
router.include_router(messages.router)
router.include_router(streaming.router)
