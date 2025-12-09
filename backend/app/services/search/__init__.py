"""Search service package for semantic, keyword, and hybrid search.

This package provides search functionality using pgvector and PostgreSQL
full-text search with support for Reciprocal Rank Fusion (RRF).
"""

from app.services.search.search_service import SearchService

__all__ = ["SearchService"]
