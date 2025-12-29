"""Search service package for semantic, keyword, and hybrid search.

This package provides search functionality using pgvector and PostgreSQL
full-text search with support for Reciprocal Rank Fusion (RRF) and
optional LLM-based re-ranking.

Issue #601: Added QueryDecomposer for multi-concept retrieval.
"""

from app.shared.services.search.decomposer import (
    DecompositionCache,
    DecompositionResult,
    DecompositionSource,
    QueryDecomposer,
)
from app.shared.services.search.reranker import ReRanker
from app.shared.services.search.search_service import SearchService
from app.shared.services.search.structural_priors import StructuralPriorScorer

__all__ = [
    "DecompositionCache",
    "DecompositionResult",
    "DecompositionSource",
    "QueryDecomposer",
    "ReRanker",
    "SearchService",
    "StructuralPriorScorer",
]
