"""Learning path advisor agent schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from app.domains.analysis.schemas.agents.base import DataAvailabilityMixin


class LearningStep(BaseModel):
    """A single step in a personalized learning path."""

    step_number: int = Field(
        description="Sequential step number in the learning path (1-indexed)",
        ge=1,
    )
    title: str = Field(
        description=(
            "Clear, concise title for this learning step (5-10 words). "
            "Should indicate what the learner will accomplish."
        )
    )
    description: str = Field(
        description=(
            "Detailed explanation of this learning step (2-4 sentences). "
            "Include: what to learn, why it's important, how it builds on previous steps, "
            "and specific resources or actions from the content."
        )
    )
    estimated_time: str = Field(
        description=(
            "Estimated time to complete this step based on user's skill level. "
            "Examples: '30 minutes', '2 hours', '1 day', '1 week'. "
            "Consider skill level: beginners need more time, experts less."
        )
    )
    prerequisites: list[str] = Field(
        description=(
            "List of prerequisite concepts or skills needed before this step. "
            "Can reference previous steps or external knowledge. Empty list if none."
        ),
        default_factory=list,
    )
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(
        description=(
            "Difficulty level of this step:\n"
            "- 'beginner': Foundational concepts, basic usage\n"
            "- 'intermediate': Practical application, common patterns\n"
            "- 'advanced': Complex scenarios, optimization, edge cases"
        )
    )


class SkillGap(BaseModel):
    """A skill gap identified between user's current level and content requirements."""

    skill_name: str = Field(description="Name of the skill or concept the user is missing")
    importance: Literal["critical", "important", "nice-to-have"] = Field(
        description=(
            "How important this skill is for understanding the content:\n"
            "- 'critical': Must have to understand core concepts\n"
            "- 'important': Significantly improves comprehension\n"
            "- 'nice-to-have': Helpful but not essential"
        )
    )
    recommended_resource: str | None = Field(
        description=(
            "Suggested resource to fill this gap (from content or general knowledge). "
            "Can be a section reference, external link, or learning recommendation."
        ),
        default=None,
    )


class LearningPathAdvisorOutput(DataAvailabilityMixin):
    """Learning path advisor analysis output schema.

    Tier 3 Research agent that creates personalized learning sequences based on:
    - User's current skill level
    - Previous analyses (learning history from memory)
    - Content complexity and requirements
    - Identified skill gaps
    """

    learning_path: list[LearningStep] = Field(
        description=(
            "Ordered sequence of 3-8 learning steps tailored to user's skill level. "
            "Steps should build progressively, starting from user's current knowledge "
            "and leading to mastery of the content. Consider prerequisite relationships "
            "and estimated time commitments."
        ),
        min_length=3,
        max_length=8,
    )
    skill_gaps: list[SkillGap] = Field(
        description=(
            "List of 0-5 skill gaps between user's current knowledge (from memory) "
            "and content requirements. Prioritize by importance. Empty list if user "
            "has all prerequisite knowledge."
        ),
        default_factory=list,
        max_length=5,
    )
    personalization_summary: str = Field(
        description=(
            "2-3 sentence explanation of how this learning path is personalized for "
            "the user. Reference: their skill level, previous learning (from memory), "
            "identified gaps, and time estimates. Make it clear how this path adapts "
            "to their specific needs."
        )
    )
    estimated_total_time: str = Field(
        description=(
            "Total estimated time to complete entire learning path based on user's "
            "skill level. Examples: '4 hours', '2 days', '1 week'. Should be sum of "
            "individual step times, adjusted for skill level."
        )
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing the quality of this learning path. "
            "Consider: availability of user memory data, clarity of content structure, "
            "specificity of learning objectives, and appropriateness of time estimates. "
            "Lower scores if memory data is limited or content lacks clear progression."
        ),
        ge=0.0,
        le=1.0,
    )
