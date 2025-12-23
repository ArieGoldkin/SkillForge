"""Edge case generator for evaluation datasets.

This module generates edge case examples across 8 categories to test
agent robustness against unusual inputs:
1. Very Short - 1-2 word queries
2. Very Long - 10K+ word articles
3. Special Characters - Unicode, emojis, code blocks
4. Misspellings - Common typos
5. Ambiguous - Multi-agent routing challenges
6. Minimal Context - Missing key information
7. Contradictory - Self-contradicting claims
8. Multilingual - Non-English or mixed language

Usage:
    ```python
    from app.evaluation.ingestion import EdgeCaseGenerator

    generator = EdgeCaseGenerator()
    examples = generator.generate_all(examples_per_category=5)
    generator.save_dataset(examples, "datasets/edge_cases_v2.json")
    ```
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from app.core.logging import get_logger
from app.evaluation.ingestion.edge_case_templates import EdgeCaseTemplates

logger = get_logger(__name__)

# Edge case category types
EdgeCaseCategory = Literal[
    "very_short",
    "very_long",
    "special_characters",
    "misspellings",
    "ambiguous",
    "minimal_context",
    "contradictory",
    "multilingual",
]

ALL_CATEGORIES: list[EdgeCaseCategory] = [
    "very_short",
    "very_long",
    "special_characters",
    "misspellings",
    "ambiguous",
    "minimal_context",
    "contradictory",
    "multilingual",
]

# Expected behaviors for each category
EXPECTED_BEHAVIORS: dict[str, dict[str, Any]] = {
    "very_short": {
        "behavior": "graceful_degradation",
        "expected_response": "Request clarification or provide generic help",
        "max_latency_ms": 1000,
        "forbidden": ["crash", "hang", "hallucinate detailed content"],
    },
    "very_long": {
        "behavior": "graceful_degradation",
        "expected_response": "Proper chunking, summary if content exceeds limits",
        "max_latency_ms": 30000,
        "forbidden": ["memory error", "truncation without notice", "timeout"],
    },
    "special_characters": {
        "behavior": "graceful_degradation",
        "expected_response": "Normalize or strip problematic characters",
        "forbidden": ["encoding error", "garbled output", "crash on unicode"],
    },
    "misspellings": {
        "behavior": "graceful_degradation",
        "expected_response": "Fuzzy match to correct technology names",
        "forbidden": ["misroute to wrong agent", "fail to recognize common techs"],
    },
    "ambiguous": {
        "behavior": "multi_agent_routing",
        "expected_response": "Route to multiple relevant agents or request clarification",
        "forbidden": ["route to single incorrect agent", "ignore relevant aspects"],
    },
    "minimal_context": {
        "behavior": "graceful_degradation",
        "expected_response": "Request missing information or provide generic guidance",
        "forbidden": ["hallucinate missing details", "make unfounded assumptions"],
    },
    "contradictory": {
        "behavior": "conflict_detection",
        "expected_response": "Identify contradiction and flag as conflicting information",
        "forbidden": ["assert one side without noting conflict", "ignore contradiction"],
    },
    "multilingual": {
        "behavior": "graceful_degradation",
        "expected_response": "Attempt processing or respond in same language if possible",
        "forbidden": ["crash on non-ASCII", "garbled response", "ignore content"],
    },
}


@dataclass
class EdgeCaseConfig:
    """Configuration for edge case generation.

    Attributes:
        category: Edge case category to generate.
        count: Number of examples to generate.
        difficulty: Difficulty level (hard or adversarial).

    """

    category: EdgeCaseCategory
    count: int = 5
    difficulty: Literal["hard", "adversarial"] = "hard"


@dataclass
class EdgeCaseGenerator:
    """Generate edge case examples for evaluation dataset.

    Generates examples across 8 categories to test agent robustness.
    All examples are v2.0 schema compliant with edge_case: true.

    Attributes:
        templates: Edge case templates instance.

    """

    templates: EdgeCaseTemplates = field(default_factory=EdgeCaseTemplates)

    def generate_all(self, examples_per_category: int = 5) -> list[dict[str, Any]]:
        """Generate all edge cases across 8 categories.

        Args:
            examples_per_category: Number of examples per category (default 5).

        Returns:
            List of 8 * examples_per_category examples in v2.0 format.

        """
        all_examples: list[dict[str, Any]] = []

        for category in ALL_CATEGORIES:
            try:
                examples = self.generate_category(category, examples_per_category)
                all_examples.extend(examples)
                logger.info(
                    "category_generated",
                    category=category,
                    count=len(examples),
                )
            except Exception as e:
                logger.error(
                    "category_generation_failed",
                    category=category,
                    error=str(e),
                )

        logger.info(
            "all_edge_cases_generated",
            total=len(all_examples),
            categories=len(ALL_CATEGORIES),
        )

        return all_examples

    def generate_category(
        self,
        category: EdgeCaseCategory,
        count: int = 5,
    ) -> list[dict[str, Any]]:
        """Generate examples for a specific category.

        Args:
            category: Edge case category to generate.
            count: Number of examples to generate.

        Returns:
            List of examples in v2.0 format.

        """
        generators = {
            "very_short": self._generate_very_short,
            "very_long": self._generate_very_long,
            "special_characters": self._generate_special_characters,
            "misspellings": self._generate_misspellings,
            "ambiguous": self._generate_ambiguous,
            "minimal_context": self._generate_minimal_context,
            "contradictory": self._generate_contradictory,
            "multilingual": self._generate_multilingual,
        }

        generator_fn = generators.get(category)
        if not generator_fn:
            msg = f"Unknown category: {category}"
            raise ValueError(msg)

        return generator_fn(count)

    def _generate_very_short(self, count: int) -> list[dict[str, Any]]:
        """Generate very short (1-2 word) query examples.

        Args:
            count: Number of examples to generate.

        Returns:
            List of very short query examples.

        """
        templates = self.templates.get_very_short_queries()
        selected = templates[:count] if len(templates) >= count else templates

        examples = []
        for i, template in enumerate(selected, 1):
            example = self._build_example(
                example_id=f"edge-short-{i:03d}",
                content=template["content"],
                content_type="query",
                category="very_short",
                difficulty="hard",
                notes=template["note"],
                expected_error=(
                    "Query too short for meaningful analysis. Please provide more context."
                ),
            )
            examples.append(example)

        return examples

    def _generate_very_long(self, count: int) -> list[dict[str, Any]]:
        """Generate very long (10K+ word) content examples.

        Args:
            count: Number of examples to generate.

        Returns:
            List of very long content examples.

        """
        examples = []
        word_counts = [10000, 12000, 15000, 18000, 20000]

        for i in range(count):
            word_count = word_counts[i % len(word_counts)]
            content = self.templates.generate_long_content(word_count)
            actual_words = len(content.split())

            example = self._build_example(
                example_id=f"edge-long-{i + 1:03d}",
                content=content,
                content_type="article",
                category="very_long",
                difficulty="hard",
                notes=f"Very long content: {actual_words} words",
            )
            examples.append(example)

        return examples

    def _generate_special_characters(self, count: int) -> list[dict[str, Any]]:
        """Generate special character content examples.

        Args:
            count: Number of examples to generate.

        Returns:
            List of special character examples.

        """
        templates = self.templates.get_special_char_templates()
        selected = templates[:count] if len(templates) >= count else templates

        examples = []
        for i, template in enumerate(selected, 1):
            example = self._build_example(
                example_id=f"edge-special-{i:03d}",
                content=template["content"],
                content_type="article",
                category="special_characters",
                difficulty="hard",
                notes=template["note"],
            )
            examples.append(example)

        return examples

    def _generate_misspellings(self, count: int) -> list[dict[str, Any]]:
        """Generate misspelling content examples.

        Args:
            count: Number of examples to generate.

        Returns:
            List of misspelling examples.

        """
        examples = []

        # Pre-defined misspelling examples for consistency
        misspelling_examples = [
            ("Reavt vs Veu comparison for modern web apps", ["React", "Vue"]),
            ("Pytohn FastAPi tutorial for beginners", ["Python", "FastAPI"]),
            ("TypeScipt authentication with Angualr", ["TypeScript", "Angular"]),
            ("Postgress database setup with Dokcer", ["PostgreSQL", "Docker"]),
            ("Kuberneets deployment for MongDB application", ["Kubernetes", "MongoDB"]),
        ]

        for i, (content, _original_terms) in enumerate(misspelling_examples[:count], 1):
            example = self._build_example(
                example_id=f"edge-typo-{i:03d}",
                content=content,
                content_type="query",
                category="misspellings",
                difficulty="hard",
                notes="Contains common technology misspellings",
            )
            examples.append(example)

        return examples

    def _generate_ambiguous(self, count: int) -> list[dict[str, Any]]:
        """Generate ambiguous (multi-agent) content examples.

        Args:
            count: Number of examples to generate.

        Returns:
            List of ambiguous content examples.

        """
        templates = self.templates.get_ambiguous_templates()
        selected = templates[:count] if len(templates) >= count else templates

        examples = []
        for i, template in enumerate(selected, 1):
            agents = template.get("agents", [])
            example = self._build_example(
                example_id=f"edge-ambig-{i:03d}",
                content=str(template["content"]),
                content_type="query",
                category="ambiguous",
                difficulty="hard",
                notes=f"Could route to {len(agents)} agents: {', '.join(str(a) for a in agents)}",
                potential_agents=agents if isinstance(agents, list) else [],
            )
            examples.append(example)

        return examples

    def _generate_minimal_context(self, count: int) -> list[dict[str, Any]]:
        """Generate minimal context content examples.

        Args:
            count: Number of examples to generate.

        Returns:
            List of minimal context examples.

        """
        templates = self.templates.get_minimal_context_templates()
        selected = templates[:count] if len(templates) >= count else templates

        examples = []
        for i, template in enumerate(selected, 1):
            example = self._build_example(
                example_id=f"edge-minimal-{i:03d}",
                content=template["content"],
                content_type="query",
                category="minimal_context",
                difficulty="hard",
                notes=f"Missing: {template.get('missing', 'key information')}",
                expected_error="Insufficient context provided. Please specify additional details.",
            )
            examples.append(example)

        return examples

    def _generate_contradictory(self, count: int) -> list[dict[str, Any]]:
        """Generate contradictory content examples.

        Args:
            count: Number of examples to generate.

        Returns:
            List of contradictory content examples.

        """
        templates = self.templates.get_contradictory_templates()
        selected = templates[:count] if len(templates) >= count else templates

        examples = []
        for i, template in enumerate(selected, 1):
            example = self._build_example(
                example_id=f"edge-contra-{i:03d}",
                content=template["content"],
                content_type="article",
                category="contradictory",
                difficulty="adversarial",  # Contradictory is adversarial
                notes=f"Contains contradictory {template.get('contradiction', 'claims')}",
            )
            examples.append(example)

        return examples

    def _generate_multilingual(self, count: int) -> list[dict[str, Any]]:
        """Generate multilingual content examples.

        Args:
            count: Number of examples to generate.

        Returns:
            List of multilingual examples.

        """
        templates = self.templates.get_multilingual_templates()
        selected = templates[:count] if len(templates) >= count else templates

        examples = []
        for i, template in enumerate(selected, 1):
            example = self._build_example(
                example_id=f"edge-multi-{i:03d}",
                content=template["content"],
                content_type="query",
                category="multilingual",
                difficulty="hard",
                notes=f"Language: {template.get('language', 'non-English')}",
            )
            examples.append(example)

        return examples

    def _build_example(
        self,
        example_id: str,
        content: str,
        content_type: str,
        category: str,
        difficulty: Literal["hard", "adversarial"],
        notes: str,
        expected_error: str | None = None,
        potential_agents: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build v2.0 schema-compliant example with edge_case: true.

        Args:
            example_id: Unique example ID.
            content: Input content.
            content_type: Type of content (query, article, code).
            category: Edge case category.
            difficulty: Difficulty level.
            notes: Notes about the example.
            expected_error: Expected error message (optional).
            potential_agents: List of potential agents for ambiguous cases.

        Returns:
            Example dictionary in v2.0 format.

        """
        behavior = EXPECTED_BEHAVIORS.get(category, {})

        # Build expected outputs based on category behavior
        primary_output: dict[str, Any] = {
            "behavior": behavior.get("behavior", "graceful_degradation"),
            "expected_response": behavior.get("expected_response", ""),
        }

        if expected_error:
            primary_output["expected_error"] = expected_error

        if potential_agents:
            primary_output["potential_agents"] = potential_agents

        # Build forbidden outputs
        forbidden_behaviors = behavior.get("forbidden", [])
        forbidden_outputs = [{"note": f"Should NOT {fb}"} for fb in forbidden_behaviors]

        return {
            "id": example_id,
            "inputs": {
                "content": content,
                "content_type": content_type,
            },
            "expected_outputs": {
                "primary": primary_output,
                "acceptable_alternatives": [],
                "forbidden_outputs": forbidden_outputs,
            },
            "evaluation_criteria": {
                "scoring_rubric": {
                    "correctness": {
                        "weight": 0.4,
                        "thresholds": {"perfect": 1.0, "acceptable": 0.6, "failing": 0.3},
                        "description": "Handles edge case appropriately without errors",
                    },
                    "completeness": {
                        "weight": 0.3,
                        "required_fields": [],
                        "description": "Provides meaningful response or graceful degradation",
                    },
                    "quality": {
                        "weight": 0.3,
                        "min_length": 10,
                        "max_length": 2000,
                        "description": "Response quality and helpfulness",
                    },
                },
                "custom_evaluators": [],
            },
            "provenance": {
                "source": "synthetic",
                "created_at": datetime.now(UTC).isoformat(),
                "created_by": "edge_case_generator",
                "notes": f"Edge case for {category} testing",
            },
            "validation": {
                "status": "draft",
                "validated_by": [],
                "quality_score": None,
            },
            "metadata": {
                "difficulty": difficulty,
                "edge_case": True,
                "adversarial": difficulty == "adversarial",
                "tags": ["edge-case", category, "robustness"],
                "edge_case_category": category,
                "notes": notes,
            },
        }

    def save_dataset(
        self,
        examples: list[dict[str, Any]],
        output_path: str | Path,
        dataset_name: str | None = None,
    ) -> None:
        """Save generated examples as v2.0 dataset.

        Args:
            examples: List of examples in v2.0 format.
            output_path: Path to save dataset JSON.
            dataset_name: Dataset name (defaults to filename).

        """
        output_path = Path(output_path)

        # Collect categories and difficulties
        categories = list(set(ex["metadata"]["edge_case_category"] for ex in examples))
        difficulties = list(set(ex["metadata"]["difficulty"] for ex in examples))

        # Build dataset
        dataset = {
            "version": "2.0.0",
            "metadata": {
                "dataset_name": dataset_name or output_path.stem,
                "task_type": "edge_case",
                "agent_types": [],  # Edge cases test all agents
                "domains": [],  # Edge cases are domain-agnostic
                "categories": categories,
                "difficulties": difficulties,
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
                "release_tag": "draft",
                "description": (
                    f"Edge case examples for agent robustness testing ({len(examples)} examples)"
                ),
                "maintainers": ["edge_case_generator"],
            },
            "examples": examples,
        }

        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)

        logger.info(
            "edge_case_dataset_saved",
            path=str(output_path),
            example_count=len(examples),
            categories=categories,
        )
