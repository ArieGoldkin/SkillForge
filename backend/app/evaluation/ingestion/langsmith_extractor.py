"""LangSmith trace extractor for evaluation datasets v2.0.

This module extracts high-quality examples from production LangSmith traces
and converts them into v2.0 evaluation dataset format.

Selection criteria:
- Confidence score ≥ threshold (default 0.85)
- No errors in trace
- Latency within acceptable bounds
- User feedback positive (if available)

Usage:
    ```bash
    python -m app.evaluation.ingestion.langsmith_extractor \
      --project-name skillforge-prod \
      --task-type agent \
      --agent-type security_auditor \
      --min-confidence 0.85 \
      --date-range 2025-12-01:2025-12-10 \
      --output datasets/drafts/langsmith_security_20251210.json
    ```

"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from langsmith import Client

from app.core.logging import get_logger

logger = get_logger(__name__)

TaskType = Literal["supervisor", "agent", "synthesis"]


@dataclass
class ExtractionConfig:
    """Configuration for LangSmith trace extraction.

    Attributes:
        project_name: LangSmith project name
        task_type: Type of task to extract (supervisor, agent, synthesis)
        agent_type: Specific agent type (for agent task_type)
        min_confidence: Minimum confidence score threshold (0-1)
        max_latency_ms: Maximum acceptable latency in milliseconds
        date_start: Start date for trace search
        date_end: End date for trace search
        limit: Maximum number of examples to extract

    """

    project_name: str
    task_type: TaskType
    agent_type: str | None = None
    min_confidence: float = 0.85
    max_latency_ms: int = 5000
    date_start: datetime | None = None
    date_end: datetime | None = None
    limit: int = 100


class LangSmithExtractor:
    """Extract evaluation examples from LangSmith traces.

    This class connects to LangSmith, queries traces based on criteria,
    and converts them to v2.0 evaluation dataset format.

    Example:
        ```python
        extractor = LangSmithExtractor()
        config = ExtractionConfig(
            project_name="skillforge-prod",
            task_type="agent",
            agent_type="security_auditor",
            min_confidence=0.85
        )
        examples = extractor.extract(config)
        extractor.save_dataset(examples, "datasets/drafts/langsmith_security.json")
        ```

    """

    def __init__(self):
        """Initialize extractor with LangSmith client."""
        self.client = Client()
        logger.info("langsmith_extractor_initialized")

    def extract(self, config: ExtractionConfig) -> list[dict[str, Any]]:
        """Extract examples from LangSmith traces.

        Args:
            config: Extraction configuration

        Returns:
            List of examples in v2.0 format (draft status)

        """
        logger.info(
            "extraction_starting",
            project=config.project_name,
            task_type=config.task_type,
            min_confidence=config.min_confidence,
        )

        # Query traces
        traces = self._query_traces(config)
        logger.info("traces_found", count=len(traces))

        # Convert to v2 format
        examples = []
        for trace in traces:
            try:
                example = self._convert_trace_to_example(trace, config)
                if example:
                    examples.append(example)
            except Exception as e:
                logger.warning("trace_conversion_failed", trace_id=str(trace.id), error=str(e))
                continue

        logger.info("extraction_complete", examples_extracted=len(examples))
        return examples

    def _query_traces(self, config: ExtractionConfig) -> list[Any]:
        """Query LangSmith for traces matching criteria.

        Args:
            config: Extraction configuration

        Returns:
            List of LangSmith Run objects

        """
        # Build filter
        filter_dict = {
            "project": config.project_name,
        }

        # Add date range if specified
        if config.date_start or config.date_end:
            filter_dict["start_time"] = config.date_start or (datetime.utcnow() - timedelta(days=7))
            if config.date_end:
                filter_dict["end_time"] = config.date_end

        # Query runs
        try:
            runs = list(
                self.client.list_runs(
                    project_name=config.project_name,
                    start_time=filter_dict.get("start_time"),
                    end_time=filter_dict.get("end_time"),
                    is_root=True,  # Only root traces
                    limit=config.limit,
                )
            )
        except Exception as e:
            logger.error("langsmith_query_failed", error=str(e))
            return []

        # Filter by criteria
        filtered_runs = []
        for run in runs:
            # Check for errors
            if run.error:
                continue

            # Check latency
            if run.end_time and run.start_time:
                latency_ms = (run.end_time - run.start_time).total_seconds() * 1000
                if latency_ms > config.max_latency_ms:
                    continue

            # Check confidence (if available in outputs)
            if run.outputs:
                confidence = self._extract_confidence(run.outputs)
                if confidence is not None and confidence < config.min_confidence:
                    continue

            # Check agent type (for agent task type)
            if config.task_type == "agent" and config.agent_type:
                agent_type = self._extract_agent_type(run.inputs or {})
                if agent_type != config.agent_type:
                    continue

            filtered_runs.append(run)

        return filtered_runs

    def _convert_trace_to_example(self, trace: Any, config: ExtractionConfig) -> dict[str, Any] | None:
        """Convert LangSmith trace to v2.0 example format.

        Args:
            trace: LangSmith Run object
            config: Extraction configuration

        Returns:
            Example dictionary in v2.0 format (or None if conversion fails)

        """
        # Extract inputs
        inputs = trace.inputs or {}
        content = inputs.get("content") or inputs.get("raw_content", "")
        if not content:
            return None

        # Generate example ID
        trace_id = str(trace.id)[:8]
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        example_id = f"{config.task_type}-langsmith-{timestamp}-{trace_id}"

        # Extract outputs
        outputs = trace.outputs or {}

        # Build example structure
        example = {
            "id": example_id,
            "inputs": {
                "content": content,
                "content_type": inputs.get("content_type", "article"),
            },
            "expected_outputs": {
                "primary": self._extract_primary_outputs(outputs, config.task_type),
                "acceptable_alternatives": [],
                "forbidden_outputs": [],
            },
            "evaluation_criteria": self._generate_default_criteria(config.task_type),
            "provenance": {
                "source": "langsmith",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "created_by": "langsmith_extractor",
                "source_url": self._get_trace_url(trace, config.project_name),
                "langsmith_trace_id": str(trace.id),
                "notes": f"Extracted from production trace on {datetime.utcnow().strftime('%Y-%m-%d')}",
            },
            "validation": {
                "status": "draft",
                "validated_by": [],
                "quality_score": None,
            },
            "metadata": {
                "difficulty": self._estimate_difficulty(content),
                "edge_case": False,
                "adversarial": False,
                "tags": self._extract_tags(inputs, outputs),
                "notes": f"Trace latency: {self._calculate_latency_ms(trace)}ms",
            },
        }

        # Add agent_type for agent task type
        if config.task_type == "agent":
            example["inputs"]["agent_type"] = config.agent_type or self._extract_agent_type(inputs)

        return example

    def _extract_confidence(self, outputs: dict[str, Any]) -> float | None:
        """Extract confidence score from outputs."""
        # Try common confidence field names
        for field in ["confidence", "confidence_score"]:
            if field in outputs:
                return float(outputs[field])

        # Try nested structures
        if "supervisor_decision" in outputs:
            decision = outputs["supervisor_decision"]
            if isinstance(decision, dict) and "confidence" in decision:
                return float(decision["confidence"])

        # Try agent findings
        if "agent_findings" in outputs:
            findings = outputs["agent_findings"]
            if isinstance(findings, list) and findings:
                first_finding = findings[0]
                if isinstance(first_finding, dict) and "confidence" in first_finding:
                    return float(first_finding["confidence"])

        return None

    def _extract_agent_type(self, inputs: dict[str, Any]) -> str | None:
        """Extract agent type from inputs."""
        return inputs.get("agent_type") or inputs.get("supervisor_decision", {}).get("agents", [None])[0]

    def _extract_primary_outputs(self, outputs: dict[str, Any], task_type: TaskType) -> dict[str, Any]:
        """Extract primary expected outputs based on task type."""
        if task_type == "supervisor":
            decision = outputs.get("supervisor_decision", {})
            return {
                "selected_agents": decision.get("agents", []),
                "confidence": decision.get("confidence", 0.0),
                "reasoning": decision.get("reasoning", ""),
            }
        elif task_type == "agent":
            # Extract first agent finding
            findings = outputs.get("agent_findings", [])
            if findings:
                return findings[0]
            return {}
        elif task_type == "synthesis":
            return outputs.get("aggregated_insights", {})
        return outputs

    def _generate_default_criteria(self, task_type: TaskType) -> dict[str, Any]:
        """Generate default evaluation criteria."""
        return {
            "scoring_rubric": {
                "correctness": {
                    "weight": 0.5,
                    "thresholds": {"perfect": 1.0, "acceptable": 0.7, "failing": 0.5},
                    "description": "Accuracy of outputs compared to production trace",
                },
                "completeness": {
                    "weight": 0.3,
                    "required_fields": [],
                },
                "quality": {
                    "weight": 0.2,
                    "min_length": 50,
                    "max_length": 5000,
                    "keywords": [],
                },
            },
            "custom_evaluators": [],
        }

    def _get_trace_url(self, trace: Any, project_name: str) -> str:
        """Generate LangSmith trace URL."""
        # This is a simplified URL - actual format depends on LangSmith setup
        trace_id = str(trace.id)
        return f"https://smith.langchain.com/projects/{project_name}/traces/{trace_id}"

    def _calculate_latency_ms(self, trace: Any) -> int:
        """Calculate trace latency in milliseconds."""
        if trace.end_time and trace.start_time:
            return int((trace.end_time - trace.start_time).total_seconds() * 1000)
        return 0

    def _estimate_difficulty(self, content: str) -> str:
        """Estimate example difficulty based on content length."""
        length = len(content)
        if length < 500:
            return "easy"
        elif length < 2000:
            return "medium"
        elif length < 5000:
            return "hard"
        else:
            return "expert"

    def _extract_tags(self, inputs: dict[str, Any], outputs: dict[str, Any]) -> list[str]:
        """Extract relevant tags from inputs/outputs."""
        tags = []

        # Add content type
        if "content_type" in inputs:
            tags.append(inputs["content_type"])

        # Add agent type
        if "agent_type" in inputs:
            tags.append(inputs["agent_type"])

        # Add from LangSmith
        tags.append("langsmith")
        tags.append("production")

        return tags

    def save_dataset(
        self, examples: list[dict[str, Any]], output_path: str | Path, dataset_name: str | None = None
    ) -> None:
        """Save extracted examples as v2.0 dataset.

        Args:
            examples: List of examples in v2.0 format
            output_path: Path to save dataset JSON
            dataset_name: Dataset name (defaults to filename)

        """
        output_path = Path(output_path)

        # Infer task type from first example
        task_type = examples[0]["inputs"].get("agent_type") if examples else "unknown"
        if task_type == "unknown" and examples:
            # Try to infer from inputs
            if "agent_type" in examples[0]["inputs"]:
                task_type = "agent"
            elif "selected_agents" in examples[0]["expected_outputs"]["primary"]:
                task_type = "supervisor"
            else:
                task_type = "synthesis"

        # Build dataset
        dataset = {
            "version": "2.0.0",
            "metadata": {
                "dataset_name": dataset_name or output_path.stem,
                "task_type": task_type,
                "agent_types": list(set(ex["inputs"].get("agent_type") for ex in examples if "agent_type" in ex["inputs"])),
                "domains": [],
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "release_tag": "draft",
                "description": f"Extracted from LangSmith on {datetime.utcnow().strftime('%Y-%m-%d')}",
                "maintainers": ["langsmith_extractor"],
            },
            "examples": examples,
        }

        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(dataset, f, indent=2)

        logger.info("dataset_saved", path=str(output_path), example_count=len(examples))


# CLI entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract evaluation examples from LangSmith traces")
    parser.add_argument("--project-name", required=True, help="LangSmith project name")
    parser.add_argument(
        "--task-type",
        required=True,
        choices=["supervisor", "agent", "synthesis"],
        help="Task type to extract",
    )
    parser.add_argument("--agent-type", help="Specific agent type (for agent task type)")
    parser.add_argument("--min-confidence", type=float, default=0.85, help="Minimum confidence threshold")
    parser.add_argument("--max-latency-ms", type=int, default=5000, help="Maximum latency in milliseconds")
    parser.add_argument("--date-range", help="Date range in format YYYY-MM-DD:YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=100, help="Maximum examples to extract")
    parser.add_argument("--output", required=True, help="Output path for dataset JSON")

    args = parser.parse_args()

    # Parse date range
    date_start = None
    date_end = None
    if args.date_range:
        try:
            start_str, end_str = args.date_range.split(":")
            date_start = datetime.fromisoformat(start_str)
            date_end = datetime.fromisoformat(end_str)
        except ValueError:
            print("Error: Invalid date range format. Use YYYY-MM-DD:YYYY-MM-DD")
            exit(1)

    # Build config
    config = ExtractionConfig(
        project_name=args.project_name,
        task_type=args.task_type,  # type: ignore
        agent_type=args.agent_type,
        min_confidence=args.min_confidence,
        max_latency_ms=args.max_latency_ms,
        date_start=date_start,
        date_end=date_end,
        limit=args.limit,
    )

    # Extract
    extractor = LangSmithExtractor()
    examples = extractor.extract(config)

    if not examples:
        print("No examples extracted matching criteria")
        exit(1)

    # Save
    extractor.save_dataset(examples, args.output)
    print(f"Extracted {len(examples)} examples to {args.output}")
