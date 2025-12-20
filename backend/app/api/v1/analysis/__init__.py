"""Analysis domain API routes."""

from fastapi import APIRouter

from app.api.v1.analysis import artifacts, endpoints, library, search

router = APIRouter(tags=["analysis"])

router.include_router(endpoints.router)
router.include_router(artifacts.router)
router.include_router(search.router)
router.include_router(library.router)
