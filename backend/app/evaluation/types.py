"""Type definitions for evaluation framework.

This module provides type aliases for evaluation data structures,
replacing Langfuse-specific types with generic equivalents for
Langfuse compatibility.

The types are designed to be compatible with both:
- Langfuse's evaluate() method (if langsmith is installed)
- Langfuse's evaluation API
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass
class EvalExample:
    """Evaluation example containing input/output pairs.

    This replaces langsmith.schemas.Example for Langfuse compatibility.

    Attributes:
        id: Unique identifier for the example
        inputs: Input data dictionary
        outputs: Expected output data dictionary (optional)
        metadata: Additional metadata about the example

    """

    inputs: dict[str, Any]
    outputs: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)


@dataclass
class EvalRun:
    """Evaluation run containing execution results.

    This replaces langsmith.schemas.Run for Langfuse compatibility.

    Attributes:
        id: Unique identifier for the run
        inputs: Input data that was passed to the model
        outputs: Output data produced by the model
        start_time: When the run started
        end_time: When the run ended (optional)
        error: Error message if the run failed (optional)
        metadata: Additional metadata about the run

    """

    inputs: dict[str, Any]
    outputs: dict[str, Any]
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)


# Type aliases for backwards compatibility with existing code
Example = EvalExample
Run = EvalRun
