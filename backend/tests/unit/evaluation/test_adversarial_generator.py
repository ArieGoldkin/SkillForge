"""Unit tests for Adversarial Example Generator.

Tests cover:
- AdversarialConfig dataclass
- AdversarialTemplates methods
- AdversarialGenerator for all 6 categories
- v2.0 schema compliance
- Dataset saving functionality
"""

import json

import pytest

from app.evaluation.ingestion.adversarial_generator import (
    ALL_CATEGORIES,
    EXPECTED_BEHAVIORS,
    AdversarialConfig,
    AdversarialGenerator,
)
from app.evaluation.ingestion.adversarial_templates import (
    HALLUCINATION_TRIGGER_TEMPLATES,
    JAILBREAK_TEMPLATES,
    MISLEADING_BENCHMARK_TEMPLATES,
    OUTDATED_CONTENT_TEMPLATES,
    PROMPT_INJECTION_TEMPLATES,
    SECURITY_ANTI_PATTERN_TEMPLATES,
    AdversarialTemplates,
)


class TestAdversarialConfig:
    """Tests for AdversarialConfig dataclass."""

    def test_config_defaults(self):
        """Test AdversarialConfig has correct defaults."""
        config = AdversarialConfig(category="prompt_injection")

        assert config.category == "prompt_injection"
        assert config.count == 5

    def test_config_custom_values(self):
        """Test AdversarialConfig with custom values."""
        config = AdversarialConfig(
            category="jailbreak",
            count=10,
        )

        assert config.category == "jailbreak"
        assert config.count == 10

    def test_config_all_categories(self):
        """Test AdversarialConfig accepts all valid categories."""
        for category in ALL_CATEGORIES:
            config = AdversarialConfig(category=category)
            assert config.category == category


class TestAdversarialTemplates:
    """Tests for AdversarialTemplates class."""

    @pytest.fixture
    def templates(self):
        """Create AdversarialTemplates instance."""
        return AdversarialTemplates()

    def test_get_prompt_injection_templates(self, templates):
        """Test prompt injection templates retrieval."""
        injection_templates = templates.get_prompt_injection_templates()

        assert len(injection_templates) > 0
        assert all("content" in t for t in injection_templates)
        assert all("attack_vector" in t for t in injection_templates)
        assert all("note" in t for t in injection_templates)

    def test_get_jailbreak_templates(self, templates):
        """Test jailbreak templates retrieval."""
        jailbreak_templates = templates.get_jailbreak_templates()

        assert len(jailbreak_templates) > 0
        assert all("content" in t for t in jailbreak_templates)
        assert all("attack_vector" in t for t in jailbreak_templates)
        assert all("note" in t for t in jailbreak_templates)

    def test_get_hallucination_trigger_templates(self, templates):
        """Test hallucination trigger templates retrieval."""
        halluc_templates = templates.get_hallucination_trigger_templates()

        assert len(halluc_templates) > 0
        assert all("content" in t for t in halluc_templates)
        assert all("fake_entity" in t for t in halluc_templates)
        assert all("note" in t for t in halluc_templates)

    def test_get_security_anti_pattern_templates(self, templates):
        """Test security anti-pattern templates retrieval."""
        security_templates = templates.get_security_anti_pattern_templates()

        assert len(security_templates) > 0
        assert all("content" in t for t in security_templates)
        assert all("vulnerability" in t for t in security_templates)
        assert all("note" in t for t in security_templates)

    def test_get_misleading_benchmark_templates(self, templates):
        """Test misleading benchmark templates retrieval."""
        benchmark_templates = templates.get_misleading_benchmark_templates()

        assert len(benchmark_templates) > 0
        assert all("content" in t for t in benchmark_templates)
        assert all("false_claim" in t for t in benchmark_templates)
        assert all("note" in t for t in benchmark_templates)

    def test_get_outdated_content_templates(self, templates):
        """Test outdated content templates retrieval."""
        outdated_templates = templates.get_outdated_content_templates()

        assert len(outdated_templates) > 0
        assert all("content" in t for t in outdated_templates)
        assert all("outdated_info" in t for t in outdated_templates)
        assert all("note" in t for t in outdated_templates)

    def test_get_all_templates(self, templates):
        """Test get_all_templates returns all categories."""
        all_templates = templates.get_all_templates()

        assert len(all_templates) == 6
        assert "prompt_injection" in all_templates
        assert "jailbreak" in all_templates
        assert "hallucination_trigger" in all_templates
        assert "security_anti_pattern" in all_templates
        assert "misleading_benchmark" in all_templates
        assert "outdated_content" in all_templates

    def test_templates_return_copies(self, templates):
        """Test templates return copies, not originals."""
        injection1 = templates.get_prompt_injection_templates()
        injection2 = templates.get_prompt_injection_templates()

        # Should be different objects
        assert injection1 is not injection2

        # Modifying one shouldn't affect the other
        injection1.append({"content": "test", "attack_vector": "test", "note": "test"})
        assert len(injection1) != len(injection2)


class TestAdversarialGeneratorCategories:
    """Tests for AdversarialGenerator category methods."""

    @pytest.fixture
    def generator(self):
        """Create AdversarialGenerator instance."""
        return AdversarialGenerator()

    def test_all_categories_constant(self):
        """Test ALL_CATEGORIES constant has 6 categories."""
        assert len(ALL_CATEGORIES) == 6
        expected = {
            "prompt_injection",
            "jailbreak",
            "hallucination_trigger",
            "security_anti_pattern",
            "misleading_benchmark",
            "outdated_content",
        }
        assert set(ALL_CATEGORIES) == expected

    def test_expected_behaviors_for_all_categories(self):
        """Test EXPECTED_BEHAVIORS exists for all categories."""
        for category in ALL_CATEGORIES:
            assert category in EXPECTED_BEHAVIORS
            behavior = EXPECTED_BEHAVIORS[category]
            assert "behavior" in behavior
            assert "expected_response" in behavior
            assert "forbidden" in behavior
            assert "severity" in behavior

    def test_generate_prompt_injection(self, generator):
        """Test prompt injection generation."""
        examples = generator.generate_category("prompt_injection", count=3)

        assert len(examples) == 3
        for ex in examples:
            assert ex["id"].startswith("adv-injection-")
            assert ex["inputs"]["content_type"] == "article"
            assert ex["metadata"]["adversarial_category"] == "prompt_injection"
            assert ex["metadata"]["adversarial"] is True
            assert ex["metadata"]["severity"] == "critical"

    def test_generate_jailbreak(self, generator):
        """Test jailbreak generation."""
        examples = generator.generate_category("jailbreak", count=3)

        assert len(examples) == 3
        for ex in examples:
            assert ex["id"].startswith("adv-jailbreak-")
            assert ex["inputs"]["content_type"] == "query"
            assert ex["metadata"]["adversarial_category"] == "jailbreak"
            assert ex["metadata"]["severity"] == "critical"

    def test_generate_hallucination_trigger(self, generator):
        """Test hallucination trigger generation."""
        examples = generator.generate_category("hallucination_trigger", count=3)

        assert len(examples) == 3
        for ex in examples:
            assert ex["id"].startswith("adv-halluc-")
            assert ex["inputs"]["content_type"] == "query"
            assert ex["metadata"]["adversarial_category"] == "hallucination_trigger"
            assert ex["metadata"]["severity"] == "high"
            # Should have fake_entity in metadata
            assert "fake_entity" in ex["metadata"]

    def test_generate_security_anti_pattern(self, generator):
        """Test security anti-pattern generation."""
        examples = generator.generate_category("security_anti_pattern", count=3)

        assert len(examples) == 3
        for ex in examples:
            assert ex["id"].startswith("adv-security-")
            assert ex["inputs"]["content_type"] == "article"
            assert ex["metadata"]["adversarial_category"] == "security_anti_pattern"
            assert ex["metadata"]["severity"] == "critical"
            # Should have vulnerability_type in metadata
            assert "vulnerability_type" in ex["metadata"]

    def test_generate_misleading_benchmark(self, generator):
        """Test misleading benchmark generation."""
        examples = generator.generate_category("misleading_benchmark", count=3)

        assert len(examples) == 3
        for ex in examples:
            assert ex["id"].startswith("adv-benchmark-")
            assert ex["inputs"]["content_type"] == "article"
            assert ex["metadata"]["adversarial_category"] == "misleading_benchmark"
            assert ex["metadata"]["severity"] == "medium"
            # Should have false_claim in metadata
            assert "false_claim" in ex["metadata"]

    def test_generate_outdated_content(self, generator):
        """Test outdated content generation."""
        examples = generator.generate_category("outdated_content", count=3)

        assert len(examples) == 3
        for ex in examples:
            assert ex["id"].startswith("adv-outdated-")
            assert ex["inputs"]["content_type"] == "article"
            assert ex["metadata"]["adversarial_category"] == "outdated_content"
            assert ex["metadata"]["severity"] == "medium"
            # Should have outdated_info in metadata
            assert "outdated_info" in ex["metadata"]

    def test_invalid_category_raises_error(self, generator):
        """Test invalid category raises ValueError."""
        with pytest.raises(ValueError, match="Unknown category"):
            generator.generate_category("invalid_category", count=1)


class TestAdversarialGeneratorAll:
    """Tests for generate_all method."""

    @pytest.fixture
    def generator(self):
        """Create AdversarialGenerator instance."""
        return AdversarialGenerator()

    def test_generate_all_default(self, generator):
        """Test generating all adversarial examples with default count."""
        examples = generator.generate_all(examples_per_category=2)

        # Should have 6 categories * 2 examples = 12 total
        assert len(examples) == 12

        # Check distribution across categories
        category_counts = {}
        for ex in examples:
            cat = ex["metadata"]["adversarial_category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1

        assert len(category_counts) == 6
        for count in category_counts.values():
            assert count == 2

    def test_generate_all_full_30(self, generator):
        """Test generating all 30 adversarial examples (6 x 5)."""
        examples = generator.generate_all(examples_per_category=5)

        assert len(examples) == 30

    def test_generate_all_unique_ids(self, generator):
        """Test all generated examples have unique IDs."""
        examples = generator.generate_all(examples_per_category=3)

        ids = [ex["id"] for ex in examples]
        assert len(ids) == len(set(ids))  # All unique

    def test_generate_all_severity_distribution(self, generator):
        """Test severity distribution across categories."""
        examples = generator.generate_all(examples_per_category=2)

        severity_counts = {}
        for ex in examples:
            sev = ex["metadata"]["severity"]
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        # Should have critical, high, and medium
        assert "critical" in severity_counts
        assert "high" in severity_counts
        assert "medium" in severity_counts


class TestAdversarialGeneratorV2Schema:
    """Tests for v2.0 schema compliance."""

    @pytest.fixture
    def generator(self):
        """Create AdversarialGenerator instance."""
        return AdversarialGenerator()

    @pytest.fixture
    def sample_example(self, generator):
        """Generate a sample example for schema testing."""
        examples = generator.generate_category("prompt_injection", count=1)
        return examples[0]

    def test_example_has_id(self, sample_example):
        """Test example has ID field."""
        assert "id" in sample_example
        assert isinstance(sample_example["id"], str)
        assert len(sample_example["id"]) > 0

    def test_example_has_inputs(self, sample_example):
        """Test example has inputs with required fields."""
        assert "inputs" in sample_example
        inputs = sample_example["inputs"]
        assert "content" in inputs
        assert "content_type" in inputs

    def test_example_has_expected_outputs(self, sample_example):
        """Test example has expected_outputs with v2.0 structure."""
        assert "expected_outputs" in sample_example
        outputs = sample_example["expected_outputs"]

        assert "primary" in outputs
        assert "acceptable_alternatives" in outputs
        assert "forbidden_outputs" in outputs

        # Primary should have behavior
        assert "behavior" in outputs["primary"]
        assert "expected_response" in outputs["primary"]

        # Forbidden should be list
        assert isinstance(outputs["forbidden_outputs"], list)

    def test_example_has_evaluation_criteria(self, sample_example):
        """Test example has evaluation_criteria with scoring rubric."""
        assert "evaluation_criteria" in sample_example
        criteria = sample_example["evaluation_criteria"]

        assert "scoring_rubric" in criteria
        rubric = criteria["scoring_rubric"]

        # Check required rubric fields
        assert "correctness" in rubric
        assert "completeness" in rubric
        assert "quality" in rubric

        # Check weights
        assert rubric["correctness"]["weight"] == 0.5
        assert rubric["completeness"]["weight"] == 0.2
        assert rubric["quality"]["weight"] == 0.3

    def test_example_has_custom_evaluators(self, sample_example):
        """Test example has custom evaluators for adversarial resistance."""
        criteria = sample_example["evaluation_criteria"]
        assert "custom_evaluators" in criteria

        evaluators = criteria["custom_evaluators"]
        assert len(evaluators) > 0

        # Check adversarial_resistance evaluator
        adv_evaluator = evaluators[0]
        assert adv_evaluator["name"] == "adversarial_resistance"
        assert adv_evaluator["type"] == "llm_judge"
        assert "config" in adv_evaluator
        assert "criteria" in adv_evaluator["config"]

    def test_example_has_provenance(self, sample_example):
        """Test example has provenance with source info."""
        assert "provenance" in sample_example
        provenance = sample_example["provenance"]

        assert provenance["source"] == "synthetic"
        assert "created_at" in provenance
        assert provenance["created_by"] == "adversarial_generator"
        assert "notes" in provenance

    def test_example_has_validation(self, sample_example):
        """Test example has validation status."""
        assert "validation" in sample_example
        validation = sample_example["validation"]

        assert validation["status"] == "draft"
        assert "validated_by" in validation

    def test_example_has_metadata(self, sample_example):
        """Test example has metadata with adversarial fields."""
        assert "metadata" in sample_example
        metadata = sample_example["metadata"]

        assert metadata["difficulty"] == "adversarial"
        assert metadata["edge_case"] is False
        assert metadata["adversarial"] is True
        assert "tags" in metadata
        assert "adversarial_category" in metadata
        assert "severity" in metadata
        assert "notes" in metadata

    def test_adversarial_tags(self, sample_example):
        """Test adversarial example has appropriate tags."""
        tags = sample_example["metadata"]["tags"]

        assert "adversarial" in tags
        assert "security" in tags
        # Category should be in tags (with dashes not underscores)
        assert "prompt-injection" in tags


class TestAdversarialGeneratorForbiddenOutputs:
    """Tests for forbidden outputs in each category."""

    @pytest.fixture
    def generator(self):
        """Create AdversarialGenerator instance."""
        return AdversarialGenerator()

    @pytest.mark.parametrize(
        "category",
        ALL_CATEGORIES,
    )
    def test_forbidden_outputs_exist(self, generator, category):
        """Test all categories have forbidden outputs."""
        examples = generator.generate_category(category, count=1)
        example = examples[0]

        forbidden = example["expected_outputs"]["forbidden_outputs"]
        assert len(forbidden) > 0
        for fb in forbidden:
            assert "note" in fb
            assert fb["note"].startswith("Should NOT")

    @pytest.mark.parametrize(
        "category",
        ALL_CATEGORIES,
    )
    def test_acceptable_alternatives_exist(self, generator, category):
        """Test all categories have acceptable alternatives."""
        examples = generator.generate_category(category, count=1)
        example = examples[0]

        alternatives = example["expected_outputs"]["acceptable_alternatives"]
        assert len(alternatives) > 0
        for alt in alternatives:
            assert "note" in alt


class TestAdversarialGeneratorSaveDataset:
    """Tests for save_dataset functionality."""

    @pytest.fixture
    def generator(self):
        """Create AdversarialGenerator instance."""
        return AdversarialGenerator()

    def test_save_dataset_creates_file(self, generator, tmp_path):
        """Test save_dataset creates JSON file."""
        examples = generator.generate_category("prompt_injection", count=2)
        output_path = tmp_path / "test_adversarial.json"

        generator.save_dataset(examples, output_path)

        assert output_path.exists()

    def test_save_dataset_valid_json(self, generator, tmp_path):
        """Test saved dataset is valid JSON."""
        examples = generator.generate_category("jailbreak", count=2)
        output_path = tmp_path / "test_dataset.json"

        generator.save_dataset(examples, output_path)

        with output_path.open() as f:
            dataset = json.load(f)

        assert "version" in dataset
        assert dataset["version"] == "2.0.0"

    def test_save_dataset_metadata(self, generator, tmp_path):
        """Test saved dataset has correct metadata."""
        examples = generator.generate_all(examples_per_category=1)
        output_path = tmp_path / "full_adversarial.json"

        generator.save_dataset(examples, output_path, dataset_name="test_adversarial")

        with output_path.open() as f:
            dataset = json.load(f)

        metadata = dataset["metadata"]
        assert metadata["dataset_name"] == "test_adversarial"
        assert metadata["task_type"] == "edge_case"
        assert "created_at" in metadata
        assert "updated_at" in metadata
        assert "description" in metadata
        assert "6 examples" in metadata["description"]

        # Check domains
        assert "security" in metadata["domains"]
        assert "safety" in metadata["domains"]
        assert "robustness" in metadata["domains"]

        # Check categories collected
        assert len(metadata["categories"]) == 6

        # Check severities collected
        assert "critical" in metadata["severities"]
        assert "high" in metadata["severities"]
        assert "medium" in metadata["severities"]

    def test_save_dataset_examples_array(self, generator, tmp_path):
        """Test saved dataset has examples array."""
        examples = generator.generate_category("security_anti_pattern", count=3)
        output_path = tmp_path / "security.json"

        generator.save_dataset(examples, output_path)

        with output_path.open() as f:
            dataset = json.load(f)

        assert "examples" in dataset
        assert len(dataset["examples"]) == 3

    def test_save_dataset_creates_directory(self, generator, tmp_path):
        """Test save_dataset creates parent directories."""
        examples = generator.generate_category("prompt_injection", count=1)
        output_path = tmp_path / "subdir" / "nested" / "adversarial.json"

        generator.save_dataset(examples, output_path)

        assert output_path.exists()


class TestAdversarialTemplateConstants:
    """Tests for template constant validity."""

    def test_prompt_injection_templates_content(self):
        """Test PROMPT_INJECTION_TEMPLATES constant content."""
        assert len(PROMPT_INJECTION_TEMPLATES) >= 5
        for t in PROMPT_INJECTION_TEMPLATES:
            assert len(t["content"]) > 20
            assert t["attack_vector"] in [
                "instruction_override",
                "delimiter_confusion",
                "authority_spoofing",
                "xml_injection",
                "privilege_escalation",
                "conversation_injection",
                "code_block_escape",
            ]

    def test_jailbreak_templates_content(self):
        """Test JAILBREAK_TEMPLATES constant content."""
        assert len(JAILBREAK_TEMPLATES) >= 5
        for t in JAILBREAK_TEMPLATES:
            assert len(t["content"]) > 20
            assert t["attack_vector"] in [
                "dan_roleplay",
                "fictional_character",
                "authority_claim",
                "hypothetical_framing",
                "continuation_attack",
                "translation_attack",
                "emotional_manipulation",
            ]

    def test_hallucination_trigger_templates_content(self):
        """Test HALLUCINATION_TRIGGER_TEMPLATES constant content."""
        assert len(HALLUCINATION_TRIGGER_TEMPLATES) >= 5
        for t in HALLUCINATION_TRIGGER_TEMPLATES:
            assert len(t["content"]) > 20
            assert "fake_entity" in t

    def test_security_anti_pattern_templates_content(self):
        """Test SECURITY_ANTI_PATTERN_TEMPLATES constant content."""
        assert len(SECURITY_ANTI_PATTERN_TEMPLATES) >= 5
        for t in SECURITY_ANTI_PATTERN_TEMPLATES:
            assert len(t["content"]) > 50  # Security examples are longer
            assert "vulnerability" in t

    def test_misleading_benchmark_templates_content(self):
        """Test MISLEADING_BENCHMARK_TEMPLATES constant content."""
        assert len(MISLEADING_BENCHMARK_TEMPLATES) >= 5
        for t in MISLEADING_BENCHMARK_TEMPLATES:
            assert len(t["content"]) > 20
            assert "false_claim" in t

    def test_outdated_content_templates_content(self):
        """Test OUTDATED_CONTENT_TEMPLATES constant content."""
        assert len(OUTDATED_CONTENT_TEMPLATES) >= 5
        for t in OUTDATED_CONTENT_TEMPLATES:
            assert len(t["content"]) > 20
            assert "outdated_info" in t


class TestAdversarialGeneratorIntegration:
    """Integration tests for full adversarial generation."""

    def test_full_30_examples_integration(self):
        """Test generating and validating all 30 adversarial examples."""
        generator = AdversarialGenerator()
        examples = generator.generate_all(examples_per_category=5)

        assert len(examples) == 30

        # Verify all have required fields
        for ex in examples:
            assert "id" in ex
            assert "inputs" in ex
            assert "expected_outputs" in ex
            assert "evaluation_criteria" in ex
            assert "provenance" in ex
            assert "validation" in ex
            assert "metadata" in ex

            # Verify adversarial metadata
            assert ex["metadata"]["adversarial"] is True
            assert ex["metadata"]["edge_case"] is False
            assert ex["metadata"]["adversarial_category"] in ALL_CATEGORIES
            assert ex["metadata"]["difficulty"] == "adversarial"

    def test_save_and_reload_full_dataset(self, tmp_path):
        """Test saving and reloading full dataset preserves data."""
        generator = AdversarialGenerator()
        examples = generator.generate_all(examples_per_category=2)
        output_path = tmp_path / "full_test.json"

        generator.save_dataset(examples, output_path, dataset_name="integration_test")

        # Reload and verify
        with output_path.open() as f:
            dataset = json.load(f)

        assert len(dataset["examples"]) == 12
        assert dataset["metadata"]["dataset_name"] == "integration_test"

        # Verify examples match
        for i, ex in enumerate(dataset["examples"]):
            assert ex["id"] == examples[i]["id"]
            assert (
                ex["metadata"]["adversarial_category"]
                == examples[i]["metadata"]["adversarial_category"]
            )

    def test_category_specific_metadata(self):
        """Test each category has its specific metadata fields."""
        generator = AdversarialGenerator()

        # Prompt injection should have attack_vector
        injection = generator.generate_category("prompt_injection", count=1)[0]
        assert "attack_vector" in injection["metadata"]

        # Hallucination should have fake_entity
        halluc = generator.generate_category("hallucination_trigger", count=1)[0]
        assert "fake_entity" in halluc["metadata"]

        # Security should have vulnerability_type
        security = generator.generate_category("security_anti_pattern", count=1)[0]
        assert "vulnerability_type" in security["metadata"]

        # Benchmark should have false_claim
        benchmark = generator.generate_category("misleading_benchmark", count=1)[0]
        assert "false_claim" in benchmark["metadata"]

        # Outdated should have outdated_info
        outdated = generator.generate_category("outdated_content", count=1)[0]
        assert "outdated_info" in outdated["metadata"]
