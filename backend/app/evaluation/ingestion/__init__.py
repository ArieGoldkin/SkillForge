"""Ingestion utilities for evaluation datasets.

This module provides tools for extracting evaluation examples from various sources:
- LangSmith production traces
- GitHub issues and discussions
- Stack Overflow Q&A (planned)

Also provides PII anonymization for safe data handling.
"""

from app.evaluation.ingestion.github_importer import (
    GitHubImportConfig,
    GitHubImporter,
    GitHubIssue,
)
from app.evaluation.ingestion.langsmith_extractor import (
    LANGSMITH_AVAILABLE,
    ExtractionConfig,
)
from app.evaluation.ingestion.pii_anonymizer import (
    AnonymizedResult,
    PIIAnonymizer,
    PIIReplacement,
    get_anonymizer,
)

# LangSmithExtractor requires langsmith package
if LANGSMITH_AVAILABLE:
    from app.evaluation.ingestion.langsmith_extractor import LangSmithExtractor

    __all__ = [
        # LangSmith
        "ExtractionConfig",
        "LangSmithExtractor",
        "LANGSMITH_AVAILABLE",
        # GitHub
        "GitHubImporter",
        "GitHubImportConfig",
        "GitHubIssue",
        # PII Anonymization
        "PIIAnonymizer",
        "PIIReplacement",
        "AnonymizedResult",
        "get_anonymizer",
    ]
else:
    __all__ = [
        # LangSmith
        "ExtractionConfig",
        "LANGSMITH_AVAILABLE",
        # GitHub
        "GitHubImporter",
        "GitHubImportConfig",
        "GitHubIssue",
        # PII Anonymization
        "PIIAnonymizer",
        "PIIReplacement",
        "AnonymizedResult",
        "get_anonymizer",
    ]
