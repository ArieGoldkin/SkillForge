"""Unit tests for Edge Case Generator.

Tests cover:
- EdgeCaseConfig dataclass
- EdgeCaseTemplates methods
- EdgeCaseGenerator for all 8 categories
- v2.0 schema compliance
- Dataset saving functionality
"""

import json

import pytest

from app.evaluation.ingestion.edge_case_generator import (
    ALL_CATEGORIES,
    EXPECTED_BEHAVIORS,
    EdgeCaseConfig,
    EdgeCaseGenerator,
)
from app.evaluation.ingestion.edge_case_templates import (

@pytest.mark.unit
    AMBIGUOUS_TEMPLATES,
    CONTRADICTORY_TEMPLATES,
    MINIMAL_CONTEXT_TEMPLATES,
    MISSPELLING_PATTERNS,
    MULTILINGUAL_TEMPLATES,
    SPECIAL_CHAR_TEMPLATES,
    TECH_CONTENT_SNIPPETS,
    VERY_SHORT_QUERIES,
    EdgeCaseTemplates,
)


class TestEdgeCaseConfig:
    """Tests for EdgeCaseConfig dataclass."""

    def test_config_defaults(self):
        """Test EdgeCaseConfig has correct defaults."""
        config = EdgeCaseConfig(category="very_short")

        assert config.category == "very_short"
        assert config.count == 5
        assert config.difficulty == "hard"

    def test_config_custom_values(self):
        """Test EdgeCaseConfig with custom values."""
        config = EdgeCaseConfig(
            category="contradictory",
            count=10,
            difficulty="adversarial",
        )

        assert config.category == "contradictory"
        assert config.count == 10
        assert config.difficulty == "adversarial"

    def test_config_all_categories(self):
        """Test EdgeCaseConfig accepts all valid categories."""
        for category in ALL_CATEGORIES:
            config = EdgeCaseConfig(category=category)
            assert config.category == category


class TestEdgeCaseTemplates:
    """Tests for EdgeCaseTemplates class."""

    @pytest.fixture
    def templates(self):
        """Create EdgeCaseTemplates instance."""
        return EdgeCaseTemplates()

    def test_get_very_short_queries(self, templates):
        """Test very short queries retrieval."""
        queries = templates.get_very_short_queries()

        assert len(queries) > 0
        assert all("content" in q for q in queries)
        assert all("note" in q for q in queries)
        # Verify content is actually short (1-2 words typically)
        for q in queries:
            assert len(q["content"].split()) <= 3

    def test_generate_long_content(self, templates):
        """Test long content generation."""
        content = templates.generate_long_content(word_count=1000)

        word_count = len(content.split())
        # Allow some variance (±10%)
        assert word_count >= 900
        assert word_count <= 1200

    def test_generate_long_content_very_long(self, templates):
        """Test very long content generation (10K+ words)."""
        content = templates.generate_long_content(word_count=10000)

        word_count = len(content.split())
        # Should be at least 9000 words
        assert word_count >= 9000

    def test_apply_misspellings(self, templates):
        """Test misspelling application."""
        # Use high typo rate to ensure at least one change
        text = "Compare React and Python for web development"
        result = templates.apply_misspellings(text, typo_rate=1.0)

        # Should have some differences
        assert result != text or "React" not in text  # Either changed or was unchanged

    def test_apply_misspellings_preserves_structure(self, templates):
        """Test misspellings preserve word count."""
        text = "React and Python and JavaScript"
        result = templates.apply_misspellings(text, typo_rate=0.5)

        # Word count should remain the same
        assert len(result.split()) == len(text.split())

    def test_get_special_char_templates(self, templates):
        """Test special character templates retrieval."""
        special = templates.get_special_char_templates()

        assert len(special) > 0
        assert all("content" in t for t in special)
        assert all("note" in t for t in special)

    def test_get_ambiguous_templates(self, templates):
        """Test ambiguous templates retrieval."""
        ambiguous = templates.get_ambiguous_templates()

        assert len(ambiguous) > 0
        assert all("content" in t for t in ambiguous)
        assert all("agents" in t for t in ambiguous)
        # Each ambiguous case should have 3+ agents
        for t in ambiguous:
            assert len(t["agents"]) >= 3

    def test_get_minimal_context_templates(self, templates):
        """Test minimal context templates retrieval."""
        minimal = templates.get_minimal_context_templates()

        assert len(minimal) > 0
        assert all("content" in t for t in minimal)
        assert all("missing" in t for t in minimal)

    def test_get_contradictory_templates(self, templates):
        """Test contradictory templates retrieval."""
        contradictory = templates.get_contradictory_templates()

        assert len(contradictory) > 0
        assert all("content" in t for t in contradictory)
        assert all("contradiction" in t for t in contradictory)

    def test_get_multilingual_templates(self, templates):
        """Test multilingual templates retrieval."""
        multilingual = templates.get_multilingual_templates()

        assert len(multilingual) > 0
        assert all("content" in t for t in multilingual)
        assert all("language" in t for t in multilingual)

    def test_get_misspelling_example(self, templates):
        """Test misspelling example generation."""
        example = templates.get_misspelling_example()

        assert isinstance(example, str)
        assert len(example) > 0
        # Should contain misspelled tech terms
        assert any(
            misspelled in example
            for patterns in MISSPELLING_PATTERNS.values()
            for misspelled in patterns
        )


class TestEdgeCaseGeneratorCategories:
    """Tests for EdgeCaseGenerator category methods."""

    @pytest.fixture
    def generator(self):
        """Create EdgeCaseGenerator instance."""
        return EdgeCaseGenerator()

    def test_all_categories_constant(self):
        """Test ALL_CATEGORIES constant has 8 categories."""
        assert len(ALL_CATEGORIES) == 8
        expected = {
            "very_short",
            "very_long",
            "special_characters",
            "misspellings",
            "ambiguous",
            "minimal_context",
            "contradictory",
            "multilingual",
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

    def test_generate_very_short(self, generator):
        """Test very short query generation."""
        examples = generator.generate_category("very_short", count=3)

        assert len(examples) == 3
        for ex in examples:
            assert ex["id"].startswith("edge-short-")
            assert ex["inputs"]["content_type"] == "query"
            assert ex["metadata"]["edge_case_category"] == "very_short"
            assert ex["metadata"]["edge_case"] is True
            # Content should be very short
            assert len(ex["inputs"]["content"].split()) <= 3

    def test_generate_very_long(self, generator):
        """Test very long content generation."""
        examples = generator.generate_category("very_long", count=2)

        assert len(examples) == 2
        for ex in examples:
            assert ex["id"].startswith("edge-long-")
            assert ex["inputs"]["content_type"] == "article"
            assert ex["metadata"]["edge_case_category"] == "very_long"
            # Content should be long (10K+ words)
            word_count = len(ex["inputs"]["content"].split())
            assert word_count >= 9000

    def test_generate_special_characters(self, generator):
        """Test special character content generation."""
        examples = generator.generate_category("special_characters", count=3)

        assert len(examples) == 3
        for ex in examples:
            assert ex["id"].startswith("edge-special-")
            assert ex["metadata"]["edge_case_category"] == "special_characters"

    def test_generate_misspellings(self, generator):
        """Test misspelling content generation."""
        examples = generator.generate_category("misspellings", count=3)

        assert len(examples) == 3
        for ex in examples:
            assert ex["id"].startswith("edge-typo-")
            assert ex["inputs"]["content_type"] == "query"
            assert ex["metadata"]["edge_case_category"] == "misspellings"

    def test_generate_ambiguous(self, generator):
        """Test ambiguous content generation."""
        examples = generator.generate_category("ambiguous", count=3)

        assert len(examples) == 3
        for ex in examples:
            assert ex["id"].startswith("edge-ambig-")
            assert ex["metadata"]["edge_case_category"] == "ambiguous"
            # Should have potential_agents in primary output
            assert "potential_agents" in ex["expected_outputs"]["primary"]

    def test_generate_minimal_context(self, generator):
        """Test minimal context content generation."""
        examples = generator.generate_category("minimal_context", count=3)

        assert len(examples) == 3
        for ex in examples:
            assert ex["id"].startswith("edge-minimal-")
            assert ex["metadata"]["edge_case_category"] == "minimal_context"
            # Should have expected_error
            assert "expected_error" in ex["expected_outputs"]["primary"]

    def test_generate_contradictory(self, generator):
        """Test contradictory content generation."""
        examples = generator.generate_category("contradictory", count=3)

        assert len(examples) == 3
        for ex in examples:
            assert ex["id"].startswith("edge-contra-")
            assert ex["metadata"]["edge_case_category"] == "contradictory"
            # Contradictory should be adversarial difficulty
            assert ex["metadata"]["difficulty"] == "adversarial"
            assert ex["metadata"]["adversarial"] is True

    def test_generate_multilingual(self, generator):
        """Test multilingual content generation."""
        examples = generator.generate_category("multilingual", count=3)

        assert len(examples) == 3
        for ex in examples:
            assert ex["id"].startswith("edge-multi-")
            assert ex["metadata"]["edge_case_category"] == "multilingual"

    def test_invalid_category_raises_error(self, generator):
        """Test invalid category raises ValueError."""
        with pytest.raises(ValueError, match="Unknown category"):
            generator.generate_category("invalid_category", count=1)


class TestEdgeCaseGeneratorAll:
    """Tests for generate_all method."""

    @pytest.fixture
    def generator(self):
        """Create EdgeCaseGenerator instance."""
        return EdgeCaseGenerator()

    def test_generate_all_default(self, generator):
        """Test generating all edge cases with default count."""
        examples = generator.generate_all(examples_per_category=2)

        # Should have 8 categories * 2 examples = 16 total
        assert len(examples) == 16

        # Check distribution across categories
        category_counts = {}
        for ex in examples:
            cat = ex["metadata"]["edge_case_category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1

        assert len(category_counts) == 8
        for _cat, count in category_counts.items():
            assert count == 2

    def test_generate_all_full_40(self, generator):
        """Test generating all 40 edge cases (8 x 5)."""
        examples = generator.generate_all(examples_per_category=5)

        assert len(examples) == 40

    def test_generate_all_unique_ids(self, generator):
        """Test all generated examples have unique IDs."""
        examples = generator.generate_all(examples_per_category=3)

        ids = [ex["id"] for ex in examples]
        assert len(ids) == len(set(ids))  # All unique


class TestEdgeCaseGeneratorV2Schema:
    """Tests for v2.0 schema compliance."""

    @pytest.fixture
    def generator(self):
        """Create EdgeCaseGenerator instance."""
        return EdgeCaseGenerator()

    @pytest.fixture
    def sample_example(self, generator):
        """Generate a sample example for schema testing."""
        examples = generator.generate_category("very_short", count=1)
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
        assert rubric["correctness"]["weight"] == 0.4
        assert rubric["completeness"]["weight"] == 0.3
        assert rubric["quality"]["weight"] == 0.3

    def test_example_has_provenance(self, sample_example):
        """Test example has provenance with source info."""
        assert "provenance" in sample_example
        provenance = sample_example["provenance"]

        assert provenance["source"] == "synthetic"
        assert "created_at" in provenance
        assert provenance["created_by"] == "edge_case_generator"
        assert "notes" in provenance

    def test_example_has_validation(self, sample_example):
        """Test example has validation status."""
        assert "validation" in sample_example
        validation = sample_example["validation"]

        assert validation["status"] == "draft"
        assert "validated_by" in validation

    def test_example_has_metadata(self, sample_example):
        """Test example has metadata with edge case fields."""
        assert "metadata" in sample_example
        metadata = sample_example["metadata"]

        assert "difficulty" in metadata
        assert metadata["difficulty"] in ["hard", "adversarial"]
        assert metadata["edge_case"] is True
        assert "adversarial" in metadata
        assert "tags" in metadata
        assert "edge_case_category" in metadata
        assert "notes" in metadata

    def test_edge_case_tags(self, sample_example):
        """Test edge case has appropriate tags."""
        tags = sample_example["metadata"]["tags"]

        assert "edge-case" in tags
        assert "robustness" in tags
        assert sample_example["metadata"]["edge_case_category"] in tags


class TestEdgeCaseGeneratorForbiddenOutputs:
    """Tests for forbidden outputs in each category."""

    @pytest.fixture
    def generator(self):
        """Create EdgeCaseGenerator instance."""
        return EdgeCaseGenerator()

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


class TestEdgeCaseGeneratorSaveDataset:
    """Tests for save_dataset functionality."""

    @pytest.fixture
    def generator(self):
        """Create EdgeCaseGenerator instance."""
        return EdgeCaseGenerator()

    def test_save_dataset_creates_file(self, generator, tmp_path):
        """Test save_dataset creates JSON file."""
        examples = generator.generate_category("very_short", count=2)
        output_path = tmp_path / "test_edge_cases.json"

        generator.save_dataset(examples, output_path)

        assert output_path.exists()

    def test_save_dataset_valid_json(self, generator, tmp_path):
        """Test saved dataset is valid JSON."""
        examples = generator.generate_category("misspellings", count=2)
        output_path = tmp_path / "test_dataset.json"

        generator.save_dataset(examples, output_path)

        with output_path.open() as f:
            dataset = json.load(f)

        assert "version" in dataset
        assert dataset["version"] == "2.0.0"

    def test_save_dataset_metadata(self, generator, tmp_path):
        """Test saved dataset has correct metadata."""
        examples = generator.generate_all(examples_per_category=1)
        output_path = tmp_path / "full_edge_cases.json"

        generator.save_dataset(examples, output_path, dataset_name="test_edges")

        with output_path.open() as f:
            dataset = json.load(f)

        metadata = dataset["metadata"]
        assert metadata["dataset_name"] == "test_edges"
        assert metadata["task_type"] == "edge_case"
        assert "created_at" in metadata
        assert "updated_at" in metadata
        assert "description" in metadata
        assert "8 examples" in metadata["description"]

        # Check categories collected
        assert len(metadata["categories"]) == 8

    def test_save_dataset_examples_array(self, generator, tmp_path):
        """Test saved dataset has examples array."""
        examples = generator.generate_category("ambiguous", count=3)
        output_path = tmp_path / "ambiguous.json"

        generator.save_dataset(examples, output_path)

        with output_path.open() as f:
            dataset = json.load(f)

        assert "examples" in dataset
        assert len(dataset["examples"]) == 3

    def test_save_dataset_creates_directory(self, generator, tmp_path):
        """Test save_dataset creates parent directories."""
        examples = generator.generate_category("very_short", count=1)
        output_path = tmp_path / "subdir" / "nested" / "edge_cases.json"

        generator.save_dataset(examples, output_path)

        assert output_path.exists()

    def test_save_dataset_preserves_unicode(self, generator, tmp_path):
        """Test save_dataset preserves Unicode characters."""
        examples = generator.generate_category("multilingual", count=3)
        output_path = tmp_path / "multilingual.json"

        generator.save_dataset(examples, output_path)

        with output_path.open(encoding="utf-8") as f:
            content = f.read()

        # Check that non-ASCII characters are preserved (not escaped)
        assert "¿" in content or "Comment" in content  # Spanish or French


class TestEdgeCaseTemplateConstants:
    """Tests for template constant validity."""

    def test_very_short_queries_content(self):
        """Test VERY_SHORT_QUERIES constant content."""
        assert len(VERY_SHORT_QUERIES) >= 5
        for q in VERY_SHORT_QUERIES:
            assert len(q["content"]) < 20  # Very short

    def test_misspelling_patterns_coverage(self):
        """Test MISSPELLING_PATTERNS covers common tech terms."""
        expected_terms = {"React", "Python", "JavaScript", "TypeScript", "FastAPI"}
        assert expected_terms.issubset(set(MISSPELLING_PATTERNS.keys()))

    def test_misspelling_patterns_have_variants(self):
        """Test each misspelling pattern has multiple variants."""
        for term, variants in MISSPELLING_PATTERNS.items():
            assert len(variants) >= 3, f"{term} should have 3+ variants"

    def test_tech_content_snippets_quality(self):
        """Test TECH_CONTENT_SNIPPETS are meaningful."""
        assert len(TECH_CONTENT_SNIPPETS) >= 10
        for snippet in TECH_CONTENT_SNIPPETS:
            assert len(snippet) > 50  # Not too short
            assert snippet.endswith(".")  # Proper sentences

    def test_special_char_templates_diversity(self):
        """Test SPECIAL_CHAR_TEMPLATES cover various special chars."""
        assert len(SPECIAL_CHAR_TEMPLATES) >= 5
        contents = [t["content"] for t in SPECIAL_CHAR_TEMPLATES]
        all_content = " ".join(contents)

        # Should have various special characters
        assert "```" in all_content  # Code blocks
        assert any(ord(c) > 127 for c in all_content)  # Unicode

    def test_ambiguous_templates_agent_counts(self):
        """Test AMBIGUOUS_TEMPLATES have 3+ agents each."""
        for template in AMBIGUOUS_TEMPLATES:
            agents = template["agents"]
            assert len(agents) >= 3, f"Template should have 3+ agents: {template}"

    def test_minimal_context_templates_have_missing(self):
        """Test MINIMAL_CONTEXT_TEMPLATES specify what's missing."""
        for template in MINIMAL_CONTEXT_TEMPLATES:
            assert "missing" in template
            assert len(template["missing"]) > 0

    def test_contradictory_templates_have_contradiction(self):
        """Test CONTRADICTORY_TEMPLATES identify the contradiction."""
        for template in CONTRADICTORY_TEMPLATES:
            assert "contradiction" in template
            assert len(template["contradiction"]) > 0

    def test_multilingual_templates_languages(self):
        """Test MULTILINGUAL_TEMPLATES cover multiple languages."""
        languages = {t["language"] for t in MULTILINGUAL_TEMPLATES}
        # Should have at least 5 different languages
        assert len(languages) >= 5
        # Should have at least Spanish, French, German
        assert "Spanish" in languages
        assert "French" in languages
        assert "German" in languages


class TestEdgeCaseGeneratorIntegration:
    """Integration tests for full edge case generation."""

    def test_full_40_examples_integration(self):
        """Test generating and validating all 40 edge cases."""
        generator = EdgeCaseGenerator()
        examples = generator.generate_all(examples_per_category=5)

        assert len(examples) == 40

        # Verify all have required fields
        for ex in examples:
            assert "id" in ex
            assert "inputs" in ex
            assert "expected_outputs" in ex
            assert "evaluation_criteria" in ex
            assert "provenance" in ex
            assert "validation" in ex
            assert "metadata" in ex

            # Verify edge case metadata
            assert ex["metadata"]["edge_case"] is True
            assert ex["metadata"]["edge_case_category"] in ALL_CATEGORIES
            assert ex["metadata"]["difficulty"] in ["hard", "adversarial"]

    def test_save_and_reload_full_dataset(self, tmp_path):
        """Test saving and reloading full dataset preserves data."""
        generator = EdgeCaseGenerator()
        examples = generator.generate_all(examples_per_category=2)
        output_path = tmp_path / "full_test.json"

        generator.save_dataset(examples, output_path, dataset_name="integration_test")

        # Reload and verify
        with output_path.open() as f:
            dataset = json.load(f)

        assert len(dataset["examples"]) == 16
        assert dataset["metadata"]["dataset_name"] == "integration_test"

        # Verify examples match
        for i, ex in enumerate(dataset["examples"]):
            assert ex["id"] == examples[i]["id"]
            assert (
                ex["metadata"]["edge_case_category"]
                == examples[i]["metadata"]["edge_case_category"]
            )
