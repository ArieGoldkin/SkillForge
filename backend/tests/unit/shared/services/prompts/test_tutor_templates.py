"""Tests for tutor domain Jinja2 templates (Issue #414).

Tests template rendering, variable substitution, and error handling.
"""

import pytest

from app.shared.services.prompts.prompt_manager import TEMPLATE_MAPPING, get_prompt_manager
from app.shared.services.prompts.template_loader import TemplatePaths, render_template


class TestTutorTemplates:
    """Test tutor domain Jinja2 templates."""

    def test_syllabus_generation_template_renders(self):
        """Test syllabus generation template renders correctly."""
        result = render_template(
            TemplatePaths.TUTOR_SYLLABUS_GENERATION,
            analysis_summary="Test summary of analysis",
            user_level="intermediate",
        )

        assert "Test summary of analysis" in result
        assert "intermediate" in result
        assert "Generate a personalized curriculum" in result
        assert "2-4 sections" in result

    def test_lesson_delivery_template_renders(self):
        """Test lesson delivery template renders correctly."""
        result = render_template(
            TemplatePaths.TUTOR_LESSON_DELIVERY,
            concept="Test Concept",
            section_title="Section 1",
            lesson_title="Lesson 1",
            user_level="beginner",
            understanding_scores='{"lesson1": 0.8}',
        )

        assert "Test Concept" in result
        assert "Section 1" in result
        assert "Lesson 1" in result
        assert "beginner" in result
        assert '{"lesson1": 0.8}' in result
        assert "Deliver a lesson" in result

    def test_socratic_question_template_renders(self):
        """Test Socratic question template renders correctly."""
        result = render_template(
            TemplatePaths.TUTOR_SOCRATIC_QUESTION,
            concept="Test Concept",
            user_response="I think it works like this...",
            user_level="advanced",
        )

        assert "Test Concept" in result
        assert "I think it works like this..." in result
        assert "advanced" in result
        assert "Generate a Socratic question" in result

    def test_readiness_assessment_template_renders(self):
        """Test readiness assessment template renders correctly."""
        result = render_template(
            TemplatePaths.TUTOR_READINESS_ASSESSMENT,
            concept="Test Concept",
            user_response="User's answer here",
            understanding_scores='{"lesson1": 0.7}',
        )

        assert "Test Concept" in result
        assert "User's answer here" in result
        assert '{"lesson1": 0.7}' in result
        assert "Assess the user's understanding" in result

    def test_rephrase_explanation_template_renders(self):
        """Test rephrase explanation template renders correctly."""
        result = render_template(
            TemplatePaths.TUTOR_REPHRASE_EXPLANATION,
            concept="Test Concept",
            user_response="I don't understand",
            user_level="beginner",
            attempts=2,
        )

        assert "Test Concept" in result
        assert "I don't understand" in result
        assert "beginner" in result
        assert "2" in result
        assert "Rephrase the explanation" in result

    def test_section_review_template_renders(self):
        """Test section review template renders correctly."""
        result = render_template(
            TemplatePaths.TUTOR_SECTION_REVIEW,
            section_title="Section 1",
            concepts="Concept A, Concept B, Concept C",
            user_level="intermediate",
            understanding_scores='{"lesson1": 0.8, "lesson2": 0.7}',
        )

        assert "Section 1" in result
        assert "Concept A, Concept B, Concept C" in result
        assert "intermediate" in result
        assert '{"lesson1": 0.8, "lesson2": 0.7}' in result
        assert "Create a section review quiz" in result

    def test_reflection_template_renders(self):
        """Test reflection template renders correctly."""
        result = render_template(
            TemplatePaths.TUTOR_REFLECTION,
            syllabus_summary="Completed: Section 1, Section 2",
            understanding_scores='{"lesson1": 0.9, "lesson2": 0.8}',
        )

        assert "Completed: Section 1, Section 2" in result
        assert '{"lesson1": 0.9, "lesson2": 0.8}' in result
        assert "Guide the user in reflecting" in result

    def test_final_challenge_template_renders(self):
        """Test final challenge template renders correctly."""
        result = render_template(
            TemplatePaths.TUTOR_FINAL_CHALLENGE,
            syllabus_summary="Sections: Section 1, Section 2, Section 3",
            user_level="advanced",
            understanding_scores='{"lesson1": 0.95}',
        )

        assert "Sections: Section 1, Section 2, Section 3" in result
        assert "advanced" in result
        assert '{"lesson1": 0.95}' in result
        assert "Create a final integrative challenge" in result

    def test_template_missing_required_variable_renders_empty(self):
        """Test that missing variables render as empty strings (Jinja2 default behavior).

        Note: Our Jinja2 environment uses default undefined behavior (silent),
        not StrictUndefined. Missing variables become empty strings rather than
        raising exceptions. This is intentional for robustness in production.
        """
        result = render_template(
            TemplatePaths.TUTOR_SYLLABUS_GENERATION,
            # Missing analysis_summary and user_level - will be empty
        )
        # Template still renders, but variables are empty
        assert "Generate a personalized curriculum" in result
        assert "2-4 sections" in result

    def test_template_with_empty_string_variables(self):
        """Test templates handle empty string variables correctly."""
        result = render_template(
            TemplatePaths.TUTOR_SOCRATIC_QUESTION,
            concept="",
            user_response="",
            user_level="",
        )

        # Template should still render, even with empty values
        assert "Generate a Socratic question" in result

    def test_template_with_special_characters(self):
        """Test templates handle special characters correctly."""
        result = render_template(
            TemplatePaths.TUTOR_LESSON_DELIVERY,
            concept="Test <html> & 'quotes' \"double\"",
            section_title="Section's Title",
            lesson_title='Lesson "1"',
            user_level="beginner",
            understanding_scores='{"lesson1": 0.8}',
        )

        # Jinja2 doesn't autoescape when autoescape=False
        assert "Test <html> & 'quotes' \"double\"" in result
        assert "Section's Title" in result
        assert 'Lesson "1"' in result

    def test_template_with_very_long_content(self):
        """Test templates handle very long content correctly."""
        long_summary = "x" * 10000
        result = render_template(
            TemplatePaths.TUTOR_SYLLABUS_GENERATION,
            analysis_summary=long_summary,
            user_level="intermediate",
        )

        assert long_summary in result
        assert len(result) > 10000


class TestTutorTemplateMapping:
    """Test tutor template mappings in TEMPLATE_MAPPING."""

    def test_all_tutor_templates_mapped(self):
        """Test all tutor templates are mapped in TEMPLATE_MAPPING."""
        expected_mappings = {
            "tutor-syllabus-generation": TemplatePaths.TUTOR_SYLLABUS_GENERATION,
            "tutor-lesson-delivery": TemplatePaths.TUTOR_LESSON_DELIVERY,
            "tutor-socratic-question": TemplatePaths.TUTOR_SOCRATIC_QUESTION,
            "tutor-readiness-assessment": TemplatePaths.TUTOR_READINESS_ASSESSMENT,
            "tutor-rephrase-explanation": TemplatePaths.TUTOR_REPHRASE_EXPLANATION,
            "tutor-section-review": TemplatePaths.TUTOR_SECTION_REVIEW,
            "tutor-reflection": TemplatePaths.TUTOR_REFLECTION,
            "tutor-final-challenge": TemplatePaths.TUTOR_FINAL_CHALLENGE,
        }

        for name, path in expected_mappings.items():
            assert name in TEMPLATE_MAPPING
            assert TEMPLATE_MAPPING[name] == path


@pytest.mark.asyncio
class TestTutorPromptManagerIntegration:
    """Test tutor templates work with PromptManager."""

    async def test_syllabus_generation_via_prompt_manager(self):
        """Test syllabus generation template via PromptManager."""
        manager = get_prompt_manager()
        prompt = await manager.get_prompt(
            "tutor-syllabus-generation",
            variables={
                "analysis_summary": "Test analysis",
                "user_level": "intermediate",
            },
        )

        assert "Test analysis" in prompt
        assert "intermediate" in prompt
        assert "Generate a personalized curriculum" in prompt

    async def test_lesson_delivery_via_prompt_manager(self):
        """Test lesson delivery template via PromptManager."""
        manager = get_prompt_manager()
        prompt = await manager.get_prompt(
            "tutor-lesson-delivery",
            variables={
                "concept": "Test Concept",
                "section_title": "Section 1",
                "lesson_title": "Lesson 1",
                "user_level": "beginner",
                "understanding_scores": '{"lesson1": 0.8}',
            },
        )

        assert "Test Concept" in prompt
        assert "Section 1" in prompt

    async def test_socratic_question_via_prompt_manager(self):
        """Test Socratic question template via PromptManager."""
        manager = get_prompt_manager()
        prompt = await manager.get_prompt(
            "tutor-socratic-question",
            variables={
                "concept": "Test Concept",
                "user_response": "I think...",
                "user_level": "advanced",
            },
        )

        assert "Test Concept" in prompt
        assert "I think..." in prompt

    async def test_readiness_assessment_via_prompt_manager(self):
        """Test readiness assessment template via PromptManager."""
        manager = get_prompt_manager()
        prompt = await manager.get_prompt(
            "tutor-readiness-assessment",
            variables={
                "concept": "Test Concept",
                "user_response": "User's answer",
                "understanding_scores": '{"lesson1": 0.7}',
            },
        )

        assert "Test Concept" in prompt
        assert "User's answer" in prompt

    async def test_rephrase_explanation_via_prompt_manager(self):
        """Test rephrase explanation template via PromptManager."""
        manager = get_prompt_manager()
        prompt = await manager.get_prompt(
            "tutor-rephrase-explanation",
            variables={
                "concept": "Test Concept",
                "user_response": "I don't understand",
                "user_level": "beginner",
                "attempts": 2,
            },
        )

        assert "Test Concept" in prompt
        assert "I don't understand" in prompt
        assert "2" in prompt

    async def test_section_review_via_prompt_manager(self):
        """Test section review template via PromptManager."""
        manager = get_prompt_manager()
        prompt = await manager.get_prompt(
            "tutor-section-review",
            variables={
                "section_title": "Section 1",
                "concepts": "Concept A, Concept B",
                "user_level": "intermediate",
                "understanding_scores": '{"lesson1": 0.8}',
            },
        )

        assert "Section 1" in prompt
        assert "Concept A, Concept B" in prompt

    async def test_reflection_via_prompt_manager(self):
        """Test reflection template via PromptManager."""
        manager = get_prompt_manager()
        prompt = await manager.get_prompt(
            "tutor-reflection",
            variables={
                "syllabus_summary": "Completed: Section 1, Section 2",
                "understanding_scores": '{"lesson1": 0.9}',
            },
        )

        assert "Completed: Section 1, Section 2" in prompt
        assert '{"lesson1": 0.9}' in prompt

    async def test_final_challenge_via_prompt_manager(self):
        """Test final challenge template via PromptManager."""
        manager = get_prompt_manager()
        prompt = await manager.get_prompt(
            "tutor-final-challenge",
            variables={
                "syllabus_summary": "Sections: Section 1, Section 2",
                "user_level": "advanced",
                "understanding_scores": '{"lesson1": 0.95}',
            },
        )

        assert "Sections: Section 1, Section 2" in prompt
        assert "advanced" in prompt

    async def test_prompt_manager_invalid_template_name(self):
        """Test PromptManager raises error for invalid template name."""
        manager = get_prompt_manager()

        with pytest.raises(ValueError, match="not found"):
            await manager.get_prompt(
                "tutor-nonexistent-template",
                variables={},
            )


@pytest.mark.asyncio
class TestTutorTemplateEdgeCases:
    """Test edge cases for tutor templates."""

    async def test_template_with_numeric_attempts(self):
        """Test attempts variable works with both int and string."""
        manager = get_prompt_manager()

        # Test with int
        prompt_int = await manager.get_prompt(
            "tutor-rephrase-explanation",
            variables={
                "concept": "Test",
                "user_response": "Response",
                "user_level": "beginner",
                "attempts": 3,  # int
            },
        )

        # Test with string
        prompt_str = await manager.get_prompt(
            "tutor-rephrase-explanation",
            variables={
                "concept": "Test",
                "user_response": "Response",
                "user_level": "beginner",
                "attempts": "3",  # string
            },
        )

        # Both should contain "3"
        assert "3" in prompt_int
        assert "3" in prompt_str

    async def test_template_with_json_in_variables(self):
        """Test templates handle JSON content in variables correctly."""
        manager = get_prompt_manager()
        json_scores = '{"lesson1": 0.8, "lesson2": 0.9, "lesson3": 0.7}'

        prompt = await manager.get_prompt(
            "tutor-readiness-assessment",
            variables={
                "concept": "Test Concept",
                "user_response": "Test response",
                "understanding_scores": json_scores,
            },
        )

        # JSON should be preserved
        assert json_scores in prompt

    async def test_template_with_unicode_characters(self):
        """Test templates handle unicode characters correctly."""
        manager = get_prompt_manager()

        prompt = await manager.get_prompt(
            "tutor-lesson-delivery",
            variables={
                "concept": "Test with émojis 🎓 and unicode éèêë",
                "section_title": "Séction with àccénts",
                "lesson_title": "Lésson 日本語",
                "user_level": "intermediate",
                "understanding_scores": "{}",
            },
        )

        assert "émojis 🎓" in prompt
        assert "àccénts" in prompt
        assert "日本語" in prompt

    async def test_template_with_newlines_in_variables(self):
        """Test templates handle newlines in variables correctly."""
        manager = get_prompt_manager()

        multi_line_summary = "Line 1\nLine 2\nLine 3"
        prompt = await manager.get_prompt(
            "tutor-syllabus-generation",
            variables={
                "analysis_summary": multi_line_summary,
                "user_level": "intermediate",
            },
        )

        assert "Line 1" in prompt
        assert "Line 2" in prompt
        assert "Line 3" in prompt
