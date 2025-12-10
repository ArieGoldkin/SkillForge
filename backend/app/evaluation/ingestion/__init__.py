"""Ingestion utilities for evaluation datasets.

This module provides tools for extracting evaluation examples from various sources:
- LangSmith production traces
- GitHub issues and discussions
- Stack Overflow Q&A (planned)

"""

from app.evaluation.ingestion.langsmith_extractor import (
    LANGSMITH_AVAILABLE,
    ExtractionConfig,
)

# LangSmithExtractor requires langsmith package
if LANGSMITH_AVAILABLE:
    from app.evaluation.ingestion.langsmith_extractor import LangSmithExtractor

    __all__ = [
        "ExtractionConfig",
        "LangSmithExtractor",
        "LANGSMITH_AVAILABLE",
    ]
else:
    __all__ = [
        "ExtractionConfig",
        "LANGSMITH_AVAILABLE",
    ]
