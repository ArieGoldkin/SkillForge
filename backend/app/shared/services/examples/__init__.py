"""Example selection services for Few-Shot Prompting (Phase 1).

This module provides semantic similarity-based example selection for agent prompts.
"""

from app.shared.services.examples.schemas import AgentExample, ExampleSelectionResult
from app.shared.services.examples.selector import SemanticExampleSelector

__all__ = [
    "AgentExample",
    "ExampleSelectionResult",
    "SemanticExampleSelector",
]
