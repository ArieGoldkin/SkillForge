"""Cutting-edge topic generator for evaluation datasets.

This module generates examples for 4 cutting-edge topics (Dec 2025):
1. A2A Protocol (Google) - Agent-to-Agent communication
2. MCP Nov 2025 - Model Context Protocol updates
3. Context Engineering - Advanced prompt engineering
4. LangGraph Multi-Agent - Multi-agent orchestration

All generated examples have:
- metadata.is_cutting_edge = true
- metadata.knowledge_cutoff = "2025-12"
- Difficulty distribution: medium:1, hard:2, adversarial:1 (default)

Usage:
    ```python
    from app.evaluation.ingestion import CuttingEdgeGenerator, Topic

    generator = CuttingEdgeGenerator()
    examples = generator.generate_all()  # All topics
    generator.save_dataset(examples, "datasets/cutting_edge_v2.json")

    # Or generate specific topic
    config = CuttingEdgeConfig(topic=Topic.MCP_NOV_2025, count_per_topic=6)
    examples = generator.generate(config)
    ```
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from app.core.logging import get_logger
from app.evaluation.ingestion.cutting_edge_templates import ALL_TEMPLATES, TopicTemplate

logger = get_logger(__name__)


class Topic(str, Enum):
    """Cutting-edge topics for Dec 2025."""

    A2A_PROTOCOL = "a2a_protocol"
    MCP_NOV_2025 = "mcp_nov_2025"
    CONTEXT_ENGINEERING = "context_engineering"
    LANGGRAPH_MULTIAGENT = "langgraph_multiagent"


ALL_TOPICS: list[Topic] = [
    Topic.A2A_PROTOCOL,
    Topic.MCP_NOV_2025,
    Topic.CONTEXT_ENGINEERING,
    Topic.LANGGRAPH_MULTIAGENT,
]


@dataclass
class CuttingEdgeConfig:
    """Configuration for cutting-edge example generation.

    Attributes:
        topic: Specific topic to generate (None = all topics)
        count_per_topic: Number of examples per topic (default 4)
        difficulty_distribution: Distribution of difficulties
        (default: medium:1, hard:2, adversarial:1)
        seed: Random seed for reproducibility (default None)
        knowledge_cutoff: Knowledge cutoff date (default "2025-12")

    """

    topic: Topic | None = None
    count_per_topic: int = 4
    difficulty_distribution: dict[str, int] = field(
        default_factory=lambda: {"medium": 1, "hard": 2, "adversarial": 1}
    )
    seed: int | None = None
    knowledge_cutoff: str = "2025-12"


@dataclass
class CuttingEdgeGenerator:
    """Generate cutting-edge topic examples for evaluation dataset.

    Generates examples for Dec 2025 cutting-edge topics with v2.0 schema compliance.
    All examples have is_cutting_edge=true and knowledge_cutoff="2025-12".

    Attributes:
        templates: Topic templates (loaded from cutting_edge_templates.py)

    """

    templates: dict[str, list[TopicTemplate]] = field(default_factory=lambda: ALL_TEMPLATES)

    def generate_all(
        self,
        count_per_topic: int = 4,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        """Generate examples for all 4 cutting-edge topics.

        Args:
            count_per_topic: Number of examples per topic (default 4)
            seed: Random seed for reproducibility

        Returns:
            List of examples in v2.0 format (4 topics x count_per_topic examples)

        Example:
            ```python
            generator = CuttingEdgeGenerator()
            examples = generator.generate_all(count_per_topic=4)
            # Returns 16 examples total (4 topics x 4 examples)
            ```

        """
        config = CuttingEdgeConfig(
            topic=None,
            count_per_topic=count_per_topic,
            seed=seed,
        )
        return self.generate(config)

    def generate(self, config: CuttingEdgeConfig) -> list[dict[str, Any]]:
        """Generate cutting-edge examples based on configuration.

        Args:
            config: Configuration specifying topic, count, and difficulty

        Returns:
            List of examples in v2.0 format

        Example:
            ```python
            config = CuttingEdgeConfig(
                topic=Topic.MCP_NOV_2025,
                count_per_topic=6,
                seed=42,
            )
            examples = generator.generate(config)
            ```

        """
        if config.seed is not None:
            random.seed(config.seed)

        all_examples: list[dict[str, Any]] = []

        # Determine which topics to generate
        topics = [config.topic] if config.topic else ALL_TOPICS

        for topic in topics:
            try:
                examples = self._generate_topic(topic, config)
                all_examples.extend(examples)
                logger.info(
                    "cutting_edge_topic_generated",
                    topic=topic.value,
                    count=len(examples),
                )
            except Exception as e:
                logger.error(
                    "cutting_edge_generation_failed",
                    topic=topic.value,
                    error=str(e),
                )

        logger.info(
            "cutting_edge_generation_complete",
            total=len(all_examples),
            topics=len(topics),
        )

        return all_examples

    def _generate_topic(self, topic: Topic, config: CuttingEdgeConfig) -> list[dict[str, Any]]:
        """Generate examples for a specific topic."""
        templates = self.templates.get(topic.value, [])
        if not templates:
            msg = f"No templates found for topic: {topic.value}"
            raise ValueError(msg)

        # Build difficulty sequence
        difficulties = self._build_difficulty_sequence(
            config.count_per_topic, config.difficulty_distribution
        )

        examples = []
        for i in range(config.count_per_topic):
            template = templates[i % len(templates)]
            difficulty = difficulties[i]

            # Select query pattern
            query = random.choice(template["query_patterns"])

            example = self._build_example(
                topic=topic,
                template=template,
                query=query,
                difficulty=difficulty,
                index=i + 1,
                knowledge_cutoff=config.knowledge_cutoff,
            )
            examples.append(example)

        return examples

    def _build_difficulty_sequence(
        self, count: int, distribution: dict[str, int]
    ) -> list[Literal["medium", "hard", "adversarial"]]:
        """Build difficulty sequence based on distribution.

        Args:
            count: Total number of examples
            distribution: Distribution dict (e.g., {"medium": 1, "hard": 2, "adversarial": 1})

        Returns:
            List of difficulties matching the count

        """
        # Build base pattern from distribution
        pattern: list[Literal["medium", "hard", "adversarial"]] = []
        for diff, freq in distribution.items():
            pattern.extend([diff] * freq)  # type: ignore[list-item]

        # Repeat pattern to match count
        full_sequence = (pattern * ((count // len(pattern)) + 1))[:count]

        # Shuffle for variety
        random.shuffle(full_sequence)

        return full_sequence

    def _build_example(
        self,
        topic: Topic,
        template: TopicTemplate,
        query: str,
        difficulty: Literal["medium", "hard", "adversarial"],
        index: int,
        knowledge_cutoff: str,
    ) -> dict[str, Any]:
        """Build v2.0 schema-compliant example with is_cutting_edge=true."""
        # Generate example ID
        topic_abbrev = {
            Topic.A2A_PROTOCOL: "a2a",
            Topic.MCP_NOV_2025: "mcp",
            Topic.CONTEXT_ENGINEERING: "ctx",
            Topic.LANGGRAPH_MULTIAGENT: "lgg",
        }[topic]
        example_id = f"cutting-edge-{topic_abbrev}-{index:03d}"

        # Determine agent type based on subdomain
        agent_type = self._infer_agent_type(template["subdomain"])

        # Build expected output
        expected_output = {
            "key_concepts": template["expected_topics"],
            "keywords": template["keywords"][:5],  # Top 5 keywords
            "references": template["references"],
            "requires_knowledge_cutoff": knowledge_cutoff,
        }

        return {
            "id": example_id,
            "inputs": {
                "content": query,
                "content_type": "query",
                "agent_type": agent_type,
            },
            "expected_outputs": {
                "primary": expected_output,
                "acceptable_alternatives": [],
                "forbidden_outputs": [
                    {"note": "Should NOT use outdated information pre-2025"},
                    {"note": "Should NOT hallucinate features not in references"},
                ],
            },
            "evaluation_criteria": {
                "scoring_rubric": {
                    "correctness": {
                        "weight": 0.5,
                        "thresholds": {"perfect": 1.0, "acceptable": 0.7, "failing": 0.4},
                        "description": "Accuracy of cutting-edge topic coverage",
                    },
                    "completeness": {
                        "weight": 0.3,
                        "required_fields": ["key_concepts", "keywords", "references"],
                        "description": "Coverage of expected topics and keywords",
                    },
                    "quality": {
                        "weight": 0.2,
                        "min_length": 200,
                        "max_length": 2000,
                        "keywords": template["keywords"],
                        "description": "Response quality and depth",
                    },
                },
                "custom_evaluators": [
                    {
                        "name": "knowledge_cutoff_validator",
                        "type": "custom_function",
                        "config": {
                            "required_cutoff": knowledge_cutoff,
                            "check_references": True,
                        },
                    }
                ],
            },
            "provenance": {
                "source": "synthetic",
                "created_at": datetime.now(UTC).isoformat(),
                "created_by": "cutting_edge_generator",
                "notes": f"Cutting-edge example for {topic.value} ({template['subdomain']})",
            },
            "validation": {
                "status": "draft",
                "validated_by": [],
                "quality_score": None,
            },
            "metadata": {
                "difficulty": difficulty,
                "is_cutting_edge": True,
                "knowledge_cutoff": knowledge_cutoff,
                "edge_case": False,
                "adversarial": difficulty == "adversarial",
                "tags": [
                    "cutting-edge",
                    topic.value,
                    template["subdomain"],
                    knowledge_cutoff,
                ],
                "notes": f"Topic: {topic.value}, Subdomain: {template['subdomain']}",
            },
        }

    def _infer_agent_type(self, subdomain: str) -> str:
        """Infer agent type from subdomain."""
        # Map subdomains to agent types
        mapping = {
            "agent_communication": "integration_specialist",
            "error_handling": "code_reviewer",
            "scalability": "performance_optimizer",
            "mcp_updates": "tech_comparator",
            "resource_templates": "implementation_planner",
            "security": "security_auditor",
            "context_optimization": "content_quality_analyst",
            "multi_turn": "content_quality_analyst",
            "rag_integration": "integration_specialist",
            "orchestration": "implementation_planner",
            "routing": "implementation_planner",
            "checkpointing": "integration_specialist",
            "observability": "performance_optimizer",
        }
        return mapping.get(subdomain, "tech_comparator")

    def save_dataset(
        self,
        examples: list[dict[str, Any]],
        output_path: str | Path,
        dataset_name: str | None = None,
    ) -> None:
        """Save generated examples as v2.0 dataset.

        Args:
            examples: List of examples in v2.0 format
            output_path: Path to save dataset JSON
            dataset_name: Dataset name (defaults to filename)

        Example:
            ```python
            generator = CuttingEdgeGenerator()
            examples = generator.generate_all()
            generator.save_dataset(examples, "datasets/cutting_edge_v2.json")
            ```

        """
        output_path = Path(output_path)

        # Collect metadata
        topics = list(
            set(ex["metadata"]["tags"][1] for ex in examples if len(ex["metadata"]["tags"]) > 1)
        )
        difficulties = list(set(ex["metadata"]["difficulty"] for ex in examples))
        agent_types = list(set(ex["inputs"]["agent_type"] for ex in examples))

        # Build dataset
        dataset = {
            "version": "2.0.0",
            "metadata": {
                "dataset_name": dataset_name or output_path.stem,
                "task_type": "agent",
                "agent_types": agent_types,
                "domains": ["cutting-edge"],
                "categories": topics,
                "difficulties": difficulties,
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
                "release_tag": "cutting-edge-2025-12",
                "description": (
                    f"Cutting-edge topics for Dec 2025: A2A Protocol, MCP Nov 2025, "
                    f"Context Engineering, LangGraph Multi-Agent ({len(examples)} examples)"
                ),
                "maintainers": ["cutting_edge_generator"],
            },
            "examples": examples,
        }

        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)

        logger.info(
            "cutting_edge_dataset_saved",
            path=str(output_path),
            example_count=len(examples),
            topics=topics,
        )


def generate_all_cutting_edge(
    seed: int | None = None, count_per_topic: int = 4
) -> list[dict[str, Any]]:
    """Convenience function to generate all cutting-edge examples.

    Args:
        seed: Random seed for reproducibility
        count_per_topic: Number of examples per topic (default 4)

    Returns:
        List of examples in v2.0 format

    Example:
        ```python
        examples = generate_all_cutting_edge(seed=42, count_per_topic=4)
        print(f"Generated {len(examples)} cutting-edge examples")
        ```

    """
    generator = CuttingEdgeGenerator()
    return generator.generate_all(count_per_topic=count_per_topic, seed=seed)
