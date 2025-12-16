"""Unit tests for cutting-edge content generator module.

Tests cover:
- Generating cutting-edge examples for each topic
- Knowledge cutoff date validation
- Reference link validation
- Reproducibility with seed
- Schema compliance
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.evaluation.ingestion.cutting_edge_generator import (
    ALL_TOPICS,
    CuttingEdgeConfig,
    CuttingEdgeGenerator,
    Topic,
)
from app.evaluation.ingestion.cutting_edge_templates import ALL_TEMPLATES

@pytest.mark.unit


class TestCuttingEdgeGenerator:
    """Tests for CuttingEdgeGenerator class."""

    def test_generates_for_single_topic(self):
        """Test generating cutting-edge examples for a single topic."""
        generator = CuttingEdgeGenerator()
        config = CuttingEdgeConfig(topic=Topic.A2A_PROTOCOL, count_per_topic=5, seed=42)
        examples = generator.generate(config)

        assert len(examples) == 5
        for example in examples:
            assert example["metadata"]["is_cutting_edge"] is True
            assert "a2a_protocol" in example["metadata"]["tags"]

    def test_generates_all_topics(self):
        """Test generating cutting-edge examples for all topics."""
        generator = CuttingEdgeGenerator()
        examples = generator.generate_all(count_per_topic=3, seed=42)

        # 4 topics * 3 examples = 12 examples
        assert len(examples) == 12

        # Verify all topics are represented
        topics_found = set()
        for example in examples:
            tags = example["metadata"]["tags"]
            for topic in ALL_TOPICS:
                if topic.value in tags:
                    topics_found.add(topic.value)

        assert len(topics_found) == 4

    def test_reproducible_with_seed(self):
        """Test generation is reproducible with same seed."""
        generator = CuttingEdgeGenerator()
        config1 = CuttingEdgeConfig(topic=Topic.MCP_NOV_2025, count_per_topic=5, seed=42)
        config2 = CuttingEdgeConfig(topic=Topic.MCP_NOV_2025, count_per_topic=5, seed=42)

        examples1 = generator.generate(config1)
        examples2 = generator.generate(config2)

        # Compare query content (deterministic with same seed)
        queries1 = [ex["inputs"]["content"] for ex in examples1]
        queries2 = [ex["inputs"]["content"] for ex in examples2]
        assert queries1 == queries2

    def test_all_examples_have_cutting_edge_flag(self):
        """Test all generated examples have is_cutting_edge=True."""
        generator = CuttingEdgeGenerator()
        examples = generator.generate_all(count_per_topic=2, seed=42)

        for example in examples:
            assert example["metadata"]["is_cutting_edge"] is True

    def test_all_examples_have_knowledge_cutoff(self):
        """Test all examples have knowledge_cutoff metadata."""
        generator = CuttingEdgeGenerator()
        examples = generator.generate_all(count_per_topic=2, seed=42)

        for example in examples:
            assert "knowledge_cutoff" in example["metadata"]
            assert example["metadata"]["knowledge_cutoff"] == "2025-12"

    def test_all_examples_have_references(self):
        """Test all examples have reference links to sources."""
        generator = CuttingEdgeGenerator()
        examples = generator.generate_all(count_per_topic=2, seed=42)

        for example in examples:
            assert "references" in example["expected_outputs"]["primary"]
            references = example["expected_outputs"]["primary"]["references"]
            assert isinstance(references, list)
            assert len(references) > 0

    def test_references_are_valid_urls(self):
        """Test all reference links are valid URLs."""
        generator = CuttingEdgeGenerator()
        examples = generator.generate_all(count_per_topic=2, seed=42)

        for example in examples:
            references = example["expected_outputs"]["primary"]["references"]
            for ref in references:
                assert ref.startswith("https://")

    def test_examples_match_schema_v2(self):
        """Test generated examples comply with schema v2.0."""
        generator = CuttingEdgeGenerator()
        examples = generator.generate_all(count_per_topic=2, seed=42)

        for example in examples:
            # Required top-level fields
            assert "id" in example
            assert "inputs" in example
            assert "expected_outputs" in example
            assert "evaluation_criteria" in example
            assert "provenance" in example
            assert "validation" in example
            assert "metadata" in example

            # Inputs structure
            assert "content" in example["inputs"]
            assert "content_type" in example["inputs"]
            assert "agent_type" in example["inputs"]

            # Expected outputs structure
            assert "primary" in example["expected_outputs"]
            assert "acceptable_alternatives" in example["expected_outputs"]
            assert "forbidden_outputs" in example["expected_outputs"]

            # Metadata structure
            assert "difficulty" in example["metadata"]
            assert "is_cutting_edge" in example["metadata"]
            assert "knowledge_cutoff" in example["metadata"]
            assert "tags" in example["metadata"]

    def test_content_quality_validation(self):
        """Test generated content meets quality standards (length, detail)."""
        generator = CuttingEdgeGenerator()
        examples = generator.generate_all(count_per_topic=2, seed=42)

        for example in examples:
            # Query should be substantive
            query = example["inputs"]["content"]
            assert len(query) > 20

            # Expected output should have multiple topics
            expected = example["expected_outputs"]["primary"]
            assert len(expected["key_concepts"]) > 0
            assert len(expected["keywords"]) > 0

    def test_difficulty_distribution(self):
        """Test generated examples have appropriate difficulty distribution."""
        generator = CuttingEdgeGenerator()
        config = CuttingEdgeConfig(
            topic=Topic.A2A_PROTOCOL,
            count_per_topic=8,
            difficulty_distribution={"medium": 2, "hard": 4, "adversarial": 2},
            seed=42,
        )
        examples = generator.generate(config)

        difficulties = [ex["metadata"]["difficulty"] for ex in examples]

        # Should have all three difficulty levels
        assert "medium" in difficulties
        assert "hard" in difficulties
        assert "adversarial" in difficulties

        # Count should match distribution (8 total examples)
        assert difficulties.count("medium") == 2
        assert difficulties.count("hard") == 4
        assert difficulties.count("adversarial") == 2


class TestCuttingEdgeTemplates:
    """Tests for cutting-edge content templates."""

    @pytest.mark.parametrize(
        "topic",
        [
            Topic.A2A_PROTOCOL,
            Topic.MCP_NOV_2025,
            Topic.CONTEXT_ENGINEERING,
            Topic.LANGGRAPH_MULTIAGENT,
        ],
    )
    def test_each_topic_has_templates(self, topic: Topic):
        """Test each topic has defined templates for cutting-edge content."""
        templates = ALL_TEMPLATES.get(topic.value, [])
        assert len(templates) >= 3

    def test_templates_include_required_fields(self):
        """Test templates have all required fields."""
        for _topic_name, templates in ALL_TEMPLATES.items():
            for template in templates:
                assert "query_patterns" in template
                assert "expected_topics" in template
                assert "keywords" in template
                assert "references" in template
                assert "subdomain" in template

                # Non-empty lists
                assert len(template["query_patterns"]) > 0
                assert len(template["expected_topics"]) > 0
                assert len(template["keywords"]) > 0
                assert len(template["references"]) > 0

    def test_templates_include_recent_technology(self):
        """Test templates reference technology from 2024-2025."""
        # Check that templates reference cutting-edge technologies
        all_keywords = []
        for templates in ALL_TEMPLATES.values():
            for template in templates:
                all_keywords.extend(template["keywords"])

        # Should include modern technologies
        modern_tech_indicators = ["A2A", "MCP", "LangGraph", "2025", "Nov", "context engineering"]
        found_modern = any(
            any(indicator.lower() in keyword.lower() for keyword in all_keywords)
            for indicator in modern_tech_indicators
        )
        assert found_modern


class TestKnowledgeCutoffValidation:
    """Tests for knowledge cutoff date validation."""

    def test_knowledge_cutoff_in_metadata(self):
        """Test all cutting-edge examples have cutoff date in metadata."""
        generator = CuttingEdgeGenerator()
        examples = generator.generate_all(count_per_topic=2, seed=42)

        for example in examples:
            assert example["metadata"]["knowledge_cutoff"] == "2025-12"

    def test_custom_knowledge_cutoff(self):
        """Test configuring custom knowledge cutoff date."""
        generator = CuttingEdgeGenerator()
        config = CuttingEdgeConfig(
            topic=Topic.MCP_NOV_2025, count_per_topic=2, knowledge_cutoff="2025-11", seed=42
        )
        examples = generator.generate(config)

        for example in examples:
            assert example["metadata"]["knowledge_cutoff"] == "2025-11"


class TestReferenceValidation:
    """Tests for reference link validation."""

    def test_all_references_are_https(self):
        """Test all reference links use HTTPS."""
        for templates in ALL_TEMPLATES.values():
            for template in templates:
                for ref in template["references"]:
                    assert ref.startswith("https://")

    def test_references_from_reputable_sources(self):
        """Test references are from reputable sources."""
        reputable_domains = [
            "github.com",
            "arxiv.org",
            "langchain",
            "modelcontextprotocol",
            "anthropic",
            "openai",
            "googleblog",
        ]

        for templates in ALL_TEMPLATES.values():
            for template in templates:
                for ref in template["references"]:
                    # At least one domain should match
                    has_reputable = any(domain in ref for domain in reputable_domains)
                    assert has_reputable, f"Reference {ref} does not contain reputable domain"


class TestGeneratorConfiguration:
    """Tests for generator configuration options."""

    def test_configure_count_per_topic(self):
        """Test configuring number of examples per topic."""
        generator = CuttingEdgeGenerator()
        config = CuttingEdgeConfig(topic=Topic.A2A_PROTOCOL, count_per_topic=10, seed=42)
        examples = generator.generate(config)

        assert len(examples) == 10

    def test_save_dataset_creates_file(self, tmp_path: Path):
        """Test saving dataset to file."""
        generator = CuttingEdgeGenerator()
        examples = generator.generate_all(count_per_topic=2, seed=42)

        output_path = tmp_path / "test_dataset.json"
        generator.save_dataset(examples, output_path)

        assert output_path.exists()

        # Verify content
        with output_path.open() as f:
            data = json.load(f)

        assert data["version"] == "2.0.0"
        assert "metadata" in data
        assert "examples" in data
        assert len(data["examples"]) == len(examples)


class TestEdgeCases:
    """Tests for edge cases in generation."""

    def test_zero_count_returns_empty_list(self):
        """Test count=0 returns empty list."""
        generator = CuttingEdgeGenerator()
        config = CuttingEdgeConfig(topic=Topic.A2A_PROTOCOL, count_per_topic=0, seed=42)
        examples = generator.generate(config)

        assert len(examples) == 0

    def test_large_count_handled(self):
        """Test large count is handled gracefully."""
        generator = CuttingEdgeGenerator()
        config = CuttingEdgeConfig(topic=Topic.A2A_PROTOCOL, count_per_topic=100, seed=42)
        examples = generator.generate(config)

        # Should generate 100 examples by cycling through templates
        assert len(examples) == 100

    def test_all_topics_enum(self):
        """Test ALL_TOPICS contains all 4 topics."""
        assert len(ALL_TOPICS) == 4
        assert Topic.A2A_PROTOCOL in ALL_TOPICS
        assert Topic.MCP_NOV_2025 in ALL_TOPICS
        assert Topic.CONTEXT_ENGINEERING in ALL_TOPICS
        assert Topic.LANGGRAPH_MULTIAGENT in ALL_TOPICS
