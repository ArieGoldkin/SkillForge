"""Ingestion utilities for evaluation datasets.

This module provides tools for extracting evaluation examples from various sources:
- Langfuse production traces (via Langfuse API)
- GitHub issues and discussions
- Edge case generation
- Adversarial example generation
- Cutting-edge topics (Dec 2025)
- Stack Overflow Q&A (planned)

Also provides PII anonymization for safe data handling.
"""

from app.evaluation.ingestion.adversarial_generator import (
    ALL_CATEGORIES as ADVERSARIAL_CATEGORIES,
)
from app.evaluation.ingestion.adversarial_generator import (
    AdversarialConfig,
    AdversarialGenerator,
)
from app.evaluation.ingestion.adversarial_templates import AdversarialTemplates
from app.evaluation.ingestion.cutting_edge_generator import (
    ALL_TOPICS,
    CuttingEdgeConfig,
    CuttingEdgeGenerator,
    Topic,
    generate_all_cutting_edge,
)
from app.evaluation.ingestion.edge_case_generator import (
    ALL_CATEGORIES as EDGE_CASE_CATEGORIES,
)
from app.evaluation.ingestion.edge_case_generator import (
    EdgeCaseConfig,
    EdgeCaseGenerator,
)
from app.evaluation.ingestion.edge_case_templates import EdgeCaseTemplates
from app.evaluation.ingestion.github_importer import (
    GitHubImportConfig,
    GitHubImporter,
    GitHubIssue,
)
from app.evaluation.ingestion.pii_anonymizer import (
    AnonymizedResult,
    PIIAnonymizer,
    PIIReplacement,
    get_anonymizer,
)

__all__ = [
    # GitHub
    "GitHubImporter",
    "GitHubImportConfig",
    "GitHubIssue",
    # Edge Cases
    "EdgeCaseGenerator",
    "EdgeCaseConfig",
    "EdgeCaseTemplates",
    "EDGE_CASE_CATEGORIES",
    # Adversarial Examples
    "AdversarialGenerator",
    "AdversarialConfig",
    "AdversarialTemplates",
    "ADVERSARIAL_CATEGORIES",
    # Cutting-Edge Topics
    "CuttingEdgeGenerator",
    "CuttingEdgeConfig",
    "Topic",
    "ALL_TOPICS",
    "generate_all_cutting_edge",
    # PII Anonymization
    "PIIAnonymizer",
    "PIIReplacement",
    "AnonymizedResult",
    "get_anonymizer",
]
