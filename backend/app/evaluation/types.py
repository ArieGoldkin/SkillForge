"""Type definitions for evaluation framework.

This module provides type aliases for evaluation data structures
used by the Langfuse-based evaluation system.

The types are designed to be compatible with Langfuse's evaluation API
and custom evaluators.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass
class EvalExample:
    """Evaluation example containing input/output pairs.

    Used by Langfuse evaluation API and custom evaluators.

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

    Used by Langfuse evaluation API and custom evaluators.

    Attributes:
        id: Unique identifier for the run
        name: Name of the run/span for tracing
        run_type: Type of run (chain, llm, tool, etc.)
        inputs: Input data that was passed to the model
        outputs: Output data produced by the model
        start_time: When the run started
        end_time: When the run ended (optional)
        error: Error message if the run failed (optional)
        trace_id: ID of the parent trace for linking
        metadata: Additional metadata about the run

    """

    inputs: dict[str, Any]
    outputs: dict[str, Any]
    name: str = "run"
    run_type: str = "chain"
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    error: str | None = None
    trace_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)


# Type aliases for backwards compatibility with existing code
Example = EvalExample
Run = EvalRun
