"""Phase 2: Learning Synthesis Schema - OPTIONAL tutor system content.

This schema defines educational content for the tutor system: core concepts with
pedagogical metadata, hands-on exercises with solutions, and self-assessment tools
(quizzes + mastery checklist).

Generated in parallel with Phase 1 (core) and Phase 3 (docs). Skipped entirely
if content lacks educational value (e.g., release notes, changelogs, brief announcements).

Related: Issue #302 - Triple-Purpose Schema Enhancement
Related: Issue #299-304 - Artifact Quality Initiative
"""

from pydantic import BaseModel, Field, field_validator

from app.domains.analysis.schemas.tasks.aggregated_insights import (
    CoreConcept,
    Exercise,
    SelfAssessment,
)


class LearningSynthesisSchema(BaseModel):
    """Phase 2: Learning-oriented content - generated in parallel.

    Contains educational materials for tutor system curriculum generation:
    - Core concepts with complexity levels and related topics
    - Hands-on exercises with progressive difficulty and hints
    - Self-assessment tools (quiz questions + mastery checklist)

    This phase is OPTIONAL and skipped for content without educational value.
    When generated, it completes in ~15-20s parallel to Phase 1.

    Examples of when to SKIP this phase:
    - Release notes / changelogs (no teaching value)
    - Brief announcements / blog posts
    - Marketing content without technical depth
    - Bug reports / issue trackers

    Examples of when to INCLUDE this phase:
    - Technical tutorials / guides
    - Architecture documentation
    - Research papers / academic content
    - API documentation with examples
    - Conference talks with technical depth
    """

    core_concepts: list[CoreConcept] = Field(
        description=(
            "Fundamental concepts with pedagogical metadata. "
            "Used by tutor system for curriculum sequencing and knowledge graph building. "
            "Each concept includes: name, definition, why_it_matters, related_concepts, complexity_level. "
            "Must have 3-7 concepts for balanced learning scope."
        ),
        min_length=3,
        max_length=7,
    )

    exercises: list[Exercise] = Field(
        description=(
            "Hands-on coding exercises with progressive difficulty. "
            "Bridges theory to practice with: title, difficulty, description, hints, solution, learning_objectives. "
            "Must have 2-4 exercises for practical skill building. "
            "Order by difficulty: Beginner → Intermediate → Advanced → Expert."
        ),
        min_length=2,
        max_length=4,
    )

    self_assessment: SelfAssessment = Field(
        description=(
            "Quiz questions and mastery checklist for progress tracking. "
            "Enables tutor system to validate understanding and adapt lesson difficulty. "
            "Includes 5-10 quiz questions (mixed difficulty) and 5-10 mastery checklist items."
        )
    )

    @field_validator("core_concepts")
    @classmethod
    def validate_core_concepts_count(cls, v: list[CoreConcept]) -> list[CoreConcept]:
        """Ensure core_concepts has 3-7 items."""
        if not 3 <= len(v) <= 7:
            msg = f"core_concepts must have 3-7 items, got {len(v)}"
            raise ValueError(msg)
        return v

    @field_validator("exercises")
    @classmethod
    def validate_exercises_count(cls, v: list[Exercise]) -> list[Exercise]:
        """Ensure exercises has 2-4 items."""
        if not 2 <= len(v) <= 4:
            msg = f"exercises must have 2-4 items, got {len(v)}"
            raise ValueError(msg)
        return v

    @field_validator("core_concepts")
    @classmethod
    def validate_complexity_levels(cls, v: list[CoreConcept]) -> list[CoreConcept]:
        """Validate that complexity_level values are valid."""
        valid_levels = {"Beginner", "Intermediate", "Advanced", "Expert"}
        for concept in v:
            if concept.complexity_level not in valid_levels:
                msg = (
                    f"core_concept '{concept.name}' has invalid complexity_level "
                    f"'{concept.complexity_level}'. Must be one of: {valid_levels}"
                )
                raise ValueError(msg)
        return v

    @field_validator("exercises")
    @classmethod
    def validate_exercise_difficulty(cls, v: list[Exercise]) -> list[Exercise]:
        """Validate that exercise difficulty values are valid."""
        valid_levels = {"Beginner", "Intermediate", "Advanced", "Expert"}
        for exercise in v:
            if exercise.difficulty not in valid_levels:
                msg = (
                    f"exercise '{exercise.title}' has invalid difficulty "
                    f"'{exercise.difficulty}'. Must be one of: {valid_levels}"
                )
                raise ValueError(msg)
        return v
