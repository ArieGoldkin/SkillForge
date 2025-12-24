"""Unit tests for universal Tier 1 agent schemas.

Tests for the 4 universal agents that run on ALL content types:
- KeyInsightsOutput: Extracts 3-5 key insights with importance and novelty scoring
- ProsConsOutput: Balanced pros/cons analysis with verdict and recommendation
- AudienceFitOutput: Primary/secondary audiences with prerequisites and unsuitability
- ActionableOutput: Immediate/follow-up actions with resources and quick wins

Issue #299-304: All agents inherit DataAvailabilityMixin for graceful degradation.
"""

import pytest
from pydantic import ValidationError

from app.domains.analysis.schemas.agents.actionable import (
    Action,
    ActionableOutput,
    Resource,
)
from app.domains.analysis.schemas.agents.audience_fit import (
    Audience,
    AudienceFitOutput,
)
from app.domains.analysis.schemas.agents.key_insights import (
    KeyInsight,
    KeyInsightsOutput,
)
from app.domains.analysis.schemas.agents.pros_cons import ProsConsOutput

# ============================================================================
# KeyInsight Model Tests (8 tests)
# ============================================================================


def test_key_insight_valid_creation():
    """Test valid KeyInsight creation with all fields."""
    insight = KeyInsight(
        title="Use HNSW indexing for vector search",
        description=(
            "HNSW (Hierarchical Navigable Small World) indexing provides 5-10x "
            "faster queries than IVFFlat while maintaining 95%+ recall. Critical "
            "for production RAG systems with >100k vectors."
        ),
        importance="high",
        novelty_score=0.8,
    )
    assert insight.title == "Use HNSW indexing for vector search"
    assert "HNSW" in insight.description
    assert insight.importance == "high"
    assert insight.novelty_score == 0.8


def test_key_insight_importance_levels():
    """Test all valid importance literal values."""
    for importance in ["high", "medium", "low"]:
        insight = KeyInsight(
            title="Test insight",
            description="Test description with sufficient length for validation.",
            importance=importance,  # type: ignore
            novelty_score=0.5,
        )
        assert insight.importance == importance


def test_key_insight_invalid_importance():
    """Test invalid importance level fails validation."""
    with pytest.raises(ValidationError) as exc_info:
        KeyInsight(
            title="Test insight",
            description="Test description with sufficient length for validation.",
            importance="critical",  # Invalid - not in Literal["high", "medium", "low"]
            novelty_score=0.5,
        )
    errors = exc_info.value.errors()
    assert any("importance" in str(err["loc"]) for err in errors)


def test_key_insight_novelty_score_bounds():
    """Test novelty_score must be between 0.0 and 1.0."""
    # Valid boundary values
    insight_min = KeyInsight(
        title="Common practice",
        description="Well-known best practice that everyone should follow.",
        importance="medium",
        novelty_score=0.0,
    )
    assert insight_min.novelty_score == 0.0

    insight_max = KeyInsight(
        title="Revolutionary approach",
        description="Completely novel technique that changes everything we knew.",
        importance="high",
        novelty_score=1.0,
    )
    assert insight_max.novelty_score == 1.0

    # Invalid values
    with pytest.raises(ValidationError) as exc_info:
        KeyInsight(
            title="Test",
            description="Test description with sufficient length.",
            importance="high",
            novelty_score=-0.1,  # Below minimum
        )
    errors = exc_info.value.errors()
    assert any("novelty_score" in str(err["loc"]) for err in errors)

    with pytest.raises(ValidationError) as exc_info:
        KeyInsight(
            title="Test",
            description="Test description with sufficient length.",
            importance="high",
            novelty_score=1.1,  # Above maximum
        )
    errors = exc_info.value.errors()
    assert any("novelty_score" in str(err["loc"]) for err in errors)


def test_key_insight_title_validation():
    """Test title field validation."""
    # Valid title
    insight = KeyInsight(
        title="Valid concise title here",
        description="Detailed explanation of this insight with proper length.",
        importance="medium",
        novelty_score=0.6,
    )
    assert insight.title == "Valid concise title here"


def test_key_insight_description_validation():
    """Test description field validation."""
    # Valid description
    insight = KeyInsight(
        title="Test insight",
        description=(
            "Detailed explanation spanning multiple sentences. "
            "This provides context about why the insight matters. "
            "It also includes practical application guidance."
        ),
        importance="medium",
        novelty_score=0.6,
    )
    assert len(insight.description) > 50


def test_key_insight_type_coercion():
    """Test Pydantic type coercion for novelty_score."""
    insight = KeyInsight.model_validate(
        {
            "title": "Test",
            "description": "Test description with sufficient length for validation.",
            "importance": "high",
            "novelty_score": "0.75",  # String should convert to float
        }
    )
    assert isinstance(insight.novelty_score, float)
    assert insight.novelty_score == 0.75


def test_key_insight_immutability():
    """Test KeyInsight is a regular BaseModel (mutable unless frozen)."""
    insight = KeyInsight(
        title="Original title",
        description="Original description with sufficient length for validation.",
        importance="high",
        novelty_score=0.8,
    )
    # BaseModel is mutable by default
    insight.novelty_score = 0.9
    assert insight.novelty_score == 0.9


# ============================================================================
# KeyInsightsOutput Schema Tests (10 tests)
# ============================================================================


def test_key_insights_output_valid_creation():
    """Test valid KeyInsightsOutput creation with all fields."""
    insights = [
        KeyInsight(
            title=f"Insight {i}",
            description=f"Detailed explanation of insight {i} with sufficient length.",
            importance="high" if i == 1 else "medium",
            novelty_score=0.8 - (i * 0.1),
        )
        for i in range(1, 4)
    ]
    output = KeyInsightsOutput(
        insights=insights,
        summary="These insights highlight the importance of HNSW indexing and caching.",
        confidence_score=0.85,
    )
    assert len(output.insights) == 3
    assert output.summary.startswith("These insights")
    assert output.confidence_score == 0.85


def test_key_insights_output_min_insights():
    """Test minimum 3 insights required."""
    insights = [
        KeyInsight(
            title=f"Insight {i}",
            description=f"Detailed explanation of insight {i} with sufficient length.",
            importance="high",
            novelty_score=0.8,
        )
        for i in range(1, 4)  # Exactly 3 insights
    ]
    output = KeyInsightsOutput(
        insights=insights,
        summary="Summary of insights.",
        confidence_score=0.8,
    )
    assert len(output.insights) == 3

    # Test fewer than 3 fails
    with pytest.raises(ValidationError) as exc_info:
        KeyInsightsOutput(
            insights=insights[:2],  # Only 2 insights
            summary="Summary of insights.",
            confidence_score=0.8,
        )
    errors = exc_info.value.errors()
    assert any("insights" in str(err["loc"]) for err in errors)


def test_key_insights_output_max_insights():
    """Test maximum 5 insights allowed."""
    insights = [
        KeyInsight(
            title=f"Insight {i}",
            description=f"Detailed explanation of insight {i} with sufficient length.",
            importance="medium",
            novelty_score=0.7,
        )
        for i in range(1, 6)  # Exactly 5 insights
    ]
    output = KeyInsightsOutput(
        insights=insights,
        summary="Summary of five insights.",
        confidence_score=0.75,
    )
    assert len(output.insights) == 5

    # Test more than 5 fails
    with pytest.raises(ValidationError) as exc_info:
        KeyInsightsOutput(
            insights=[*insights, insights[0]],  # 6 insights
            summary="Summary of insights.",
            confidence_score=0.8,
        )
    errors = exc_info.value.errors()
    assert any("insights" in str(err["loc"]) for err in errors)


def test_key_insights_output_confidence_score_bounds():
    """Test confidence_score must be between 0.0 and 1.0."""
    insights = [
        KeyInsight(
            title=f"Insight {i}",
            description=f"Detailed explanation of insight {i} with sufficient length.",
            importance="high",
            novelty_score=0.8,
        )
        for i in range(1, 4)
    ]

    # Valid boundary values
    output_min = KeyInsightsOutput(
        insights=insights,
        summary="Low confidence summary.",
        confidence_score=0.0,
    )
    assert output_min.confidence_score == 0.0

    output_max = KeyInsightsOutput(
        insights=insights,
        summary="High confidence summary.",
        confidence_score=1.0,
    )
    assert output_max.confidence_score == 1.0

    # Invalid values
    with pytest.raises(ValidationError) as exc_info:
        KeyInsightsOutput(
            insights=insights,
            summary="Summary",
            confidence_score=-0.1,
        )
    errors = exc_info.value.errors()
    assert any("confidence_score" in str(err["loc"]) for err in errors)

    with pytest.raises(ValidationError) as exc_info:
        KeyInsightsOutput(
            insights=insights,
            summary="Summary",
            confidence_score=1.1,
        )
    errors = exc_info.value.errors()
    assert any("confidence_score" in str(err["loc"]) for err in errors)


def test_key_insights_output_data_availability_default():
    """Test DataAvailabilityMixin default value is 'sufficient'."""
    insights = [
        KeyInsight(
            title=f"Insight {i}",
            description=f"Detailed explanation of insight {i} with sufficient length.",
            importance="high",
            novelty_score=0.8,
        )
        for i in range(1, 4)
    ]
    output = KeyInsightsOutput(
        insights=insights,
        summary="Summary of insights.",
        confidence_score=0.8,
    )
    assert output.data_availability == "sufficient"
    assert output.data_availability_note == ""


def test_key_insights_output_data_availability_values():
    """Test all valid data_availability literal values."""
    insights = [
        KeyInsight(
            title=f"Insight {i}",
            description=f"Detailed explanation of insight {i} with sufficient length.",
            importance="high",
            novelty_score=0.8,
        )
        for i in range(1, 4)
    ]

    for availability in ["sufficient", "limited", "insufficient"]:
        output = KeyInsightsOutput(
            insights=insights,
            summary="Summary of insights.",
            confidence_score=0.7,
            data_availability=availability,  # type: ignore
            data_availability_note=f"Note for {availability}",
        )
        assert output.data_availability == availability


def test_key_insights_output_invalid_data_availability():
    """Test invalid data_availability value fails validation."""
    insights = [
        KeyInsight(
            title=f"Insight {i}",
            description=f"Detailed explanation of insight {i} with sufficient length.",
            importance="high",
            novelty_score=0.8,
        )
        for i in range(1, 4)
    ]

    with pytest.raises(ValidationError) as exc_info:
        KeyInsightsOutput(
            insights=insights,
            summary="Summary",
            confidence_score=0.8,
            data_availability="partial",  # Invalid value
        )
    errors = exc_info.value.errors()
    assert any("data_availability" in str(err["loc"]) for err in errors)


def test_key_insights_output_summary_validation():
    """Test summary field accepts strings."""
    insights = [
        KeyInsight(
            title=f"Insight {i}",
            description=f"Detailed explanation of insight {i} with sufficient length.",
            importance="high",
            novelty_score=0.8,
        )
        for i in range(1, 4)
    ]
    output = KeyInsightsOutput(
        insights=insights,
        summary="This is a comprehensive summary of all key insights extracted.",
        confidence_score=0.85,
    )
    assert len(output.summary) > 20


def test_key_insights_output_type_coercion():
    """Test Pydantic type coercion for confidence_score."""
    insights = [
        KeyInsight(
            title=f"Insight {i}",
            description=f"Detailed explanation of insight {i} with sufficient length.",
            importance="high",
            novelty_score=0.8,
        )
        for i in range(1, 4)
    ]
    output = KeyInsightsOutput.model_validate(
        {
            "insights": [
                {
                    "title": insight.title,
                    "description": insight.description,
                    "importance": insight.importance,
                    "novelty_score": insight.novelty_score,
                }
                for insight in insights
            ],
            "summary": "Summary",
            "confidence_score": "0.82",  # String should convert to float
        }
    )
    assert isinstance(output.confidence_score, float)
    assert output.confidence_score == 0.82


def test_key_insights_output_nested_validation():
    """Test nested KeyInsight models are validated."""
    with pytest.raises(ValidationError) as exc_info:
        KeyInsightsOutput.model_validate(
            {
                "insights": [
                    {
                        "title": "Valid",
                        "description": "Valid description with sufficient length.",
                        "importance": "high",
                        "novelty_score": 0.8,
                    },
                    {
                        "title": "Invalid",
                        "description": "Valid description with sufficient length.",
                        "importance": "critical",  # Invalid importance
                        "novelty_score": 0.7,
                    },
                    {
                        "title": "Also Valid",
                        "description": "Valid description with sufficient length.",
                        "importance": "low",
                        "novelty_score": 0.5,
                    },
                ],
                "summary": "Summary",
                "confidence_score": 0.8,
            }
        )
    errors = exc_info.value.errors()
    assert any("importance" in str(err["loc"]) for err in errors)


# ============================================================================
# ProsConsOutput Schema Tests (10 tests)
# ============================================================================


def test_pros_cons_output_valid_creation():
    """Test valid ProsConsOutput creation with all fields."""
    output = ProsConsOutput(
        pros=[
            "40% faster cold start times vs AWS Lambda",
            "Built-in observability with Langfuse integration",
            "Seamless streaming via Server-Sent Events",
        ],
        cons=[
            "Limited to 100 concurrent executions in free tier",
            "Requires Python 3.9+ (not compatible with older versions)",
        ],
        verdict=(
            "Excellent choice for modern RAG applications requiring streaming. "
            "The performance benefits and built-in observability outweigh the "
            "minor limitations in concurrency and Python version requirements."
        ),
        recommendation="strongly_recommended",
        confidence_score=0.88,
    )
    assert len(output.pros) == 3
    assert len(output.cons) == 2
    assert "Excellent choice" in output.verdict
    assert output.recommendation == "strongly_recommended"
    assert output.confidence_score == 0.88


def test_pros_cons_output_min_pros():
    """Test minimum 2 pros required."""
    # Valid with exactly 2 pros
    output = ProsConsOutput(
        pros=["Pro 1", "Pro 2"],
        cons=["Con 1"],
        verdict="Balanced verdict here.",
        recommendation="neutral",
        confidence_score=0.7,
    )
    assert len(output.pros) == 2

    # Invalid with only 1 pro
    with pytest.raises(ValidationError) as exc_info:
        ProsConsOutput(
            pros=["Pro 1"],  # Only 1 pro
            cons=["Con 1"],
            verdict="Verdict",
            recommendation="neutral",
            confidence_score=0.7,
        )
    errors = exc_info.value.errors()
    assert any("pros" in str(err["loc"]) for err in errors)


def test_pros_cons_output_max_pros():
    """Test maximum 7 pros allowed."""
    # Valid with exactly 7 pros
    output = ProsConsOutput(
        pros=[f"Pro {i}" for i in range(1, 8)],  # 7 pros
        cons=["Con 1"],
        verdict="Verdict with 7 pros.",
        recommendation="recommended",
        confidence_score=0.75,
    )
    assert len(output.pros) == 7

    # Invalid with 8 pros
    with pytest.raises(ValidationError) as exc_info:
        ProsConsOutput(
            pros=[f"Pro {i}" for i in range(1, 9)],  # 8 pros
            cons=["Con 1"],
            verdict="Verdict",
            recommendation="recommended",
            confidence_score=0.75,
        )
    errors = exc_info.value.errors()
    assert any("pros" in str(err["loc"]) for err in errors)


def test_pros_cons_output_min_cons():
    """Test minimum 1 con required."""
    # Valid with exactly 1 con
    output = ProsConsOutput(
        pros=["Pro 1", "Pro 2"],
        cons=["Con 1"],
        verdict="Verdict",
        recommendation="recommended",
        confidence_score=0.8,
    )
    assert len(output.cons) == 1

    # Invalid with 0 cons
    with pytest.raises(ValidationError) as exc_info:
        ProsConsOutput(
            pros=["Pro 1", "Pro 2"],
            cons=[],  # Empty list
            verdict="Verdict",
            recommendation="recommended",
            confidence_score=0.8,
        )
    errors = exc_info.value.errors()
    assert any("cons" in str(err["loc"]) for err in errors)


def test_pros_cons_output_max_cons():
    """Test maximum 7 cons allowed."""
    # Valid with exactly 7 cons
    output = ProsConsOutput(
        pros=["Pro 1", "Pro 2"],
        cons=[f"Con {i}" for i in range(1, 8)],  # 7 cons
        verdict="Verdict with 7 cons.",
        recommendation="not_recommended",
        confidence_score=0.65,
    )
    assert len(output.cons) == 7

    # Invalid with 8 cons
    with pytest.raises(ValidationError) as exc_info:
        ProsConsOutput(
            pros=["Pro 1", "Pro 2"],
            cons=[f"Con {i}" for i in range(1, 9)],  # 8 cons
            verdict="Verdict",
            recommendation="not_recommended",
            confidence_score=0.65,
        )
    errors = exc_info.value.errors()
    assert any("cons" in str(err["loc"]) for err in errors)


def test_pros_cons_output_recommendation_values():
    """Test all valid recommendation literal values."""
    for recommendation in [
        "strongly_recommended",
        "recommended",
        "neutral",
        "not_recommended",
    ]:
        output = ProsConsOutput(
            pros=["Pro 1", "Pro 2"],
            cons=["Con 1"],
            verdict="Verdict",
            recommendation=recommendation,  # type: ignore
            confidence_score=0.7,
        )
        assert output.recommendation == recommendation


def test_pros_cons_output_invalid_recommendation():
    """Test invalid recommendation value fails validation."""
    with pytest.raises(ValidationError) as exc_info:
        ProsConsOutput(
            pros=["Pro 1", "Pro 2"],
            cons=["Con 1"],
            verdict="Verdict",
            recommendation="maybe",  # Invalid value
            confidence_score=0.7,
        )
    errors = exc_info.value.errors()
    assert any("recommendation" in str(err["loc"]) for err in errors)


def test_pros_cons_output_confidence_score_bounds():
    """Test confidence_score must be between 0.0 and 1.0."""
    # Valid boundary values
    output_min = ProsConsOutput(
        pros=["Pro 1", "Pro 2"],
        cons=["Con 1"],
        verdict="Verdict",
        recommendation="neutral",
        confidence_score=0.0,
    )
    assert output_min.confidence_score == 0.0

    output_max = ProsConsOutput(
        pros=["Pro 1", "Pro 2"],
        cons=["Con 1"],
        verdict="Verdict",
        recommendation="neutral",
        confidence_score=1.0,
    )
    assert output_max.confidence_score == 1.0

    # Invalid values
    with pytest.raises(ValidationError) as exc_info:
        ProsConsOutput(
            pros=["Pro 1", "Pro 2"],
            cons=["Con 1"],
            verdict="Verdict",
            recommendation="neutral",
            confidence_score=-0.1,
        )
    errors = exc_info.value.errors()
    assert any("confidence_score" in str(err["loc"]) for err in errors)

    with pytest.raises(ValidationError) as exc_info:
        ProsConsOutput(
            pros=["Pro 1", "Pro 2"],
            cons=["Con 1"],
            verdict="Verdict",
            recommendation="neutral",
            confidence_score=1.1,
        )
    errors = exc_info.value.errors()
    assert any("confidence_score" in str(err["loc"]) for err in errors)


def test_pros_cons_output_data_availability_inheritance():
    """Test ProsConsOutput inherits DataAvailabilityMixin."""
    output = ProsConsOutput(
        pros=["Pro 1", "Pro 2"],
        cons=["Con 1"],
        verdict="Verdict",
        recommendation="neutral",
        confidence_score=0.7,
    )
    # Default values from mixin
    assert output.data_availability == "sufficient"
    assert output.data_availability_note == ""

    # Can set explicitly
    output_limited = ProsConsOutput(
        pros=["Pro 1", "Pro 2"],
        cons=["Con 1"],
        verdict="Verdict",
        recommendation="neutral",
        confidence_score=0.6,
        data_availability="limited",
        data_availability_note="Only high-level pros/cons mentioned, no quantitative data",
    )
    assert output_limited.data_availability == "limited"
    assert "quantitative" in output_limited.data_availability_note


def test_pros_cons_output_verdict_validation():
    """Test verdict field accepts strings."""
    output = ProsConsOutput(
        pros=["Pro 1", "Pro 2"],
        cons=["Con 1"],
        verdict=(
            "This is a comprehensive verdict that synthesizes both pros and cons. "
            "It provides clear guidance on when to use this technology."
        ),
        recommendation="recommended",
        confidence_score=0.82,
    )
    assert len(output.verdict) > 50


# ============================================================================
# Audience Model Tests (8 tests)
# ============================================================================


def test_audience_valid_creation():
    """Test valid Audience creation with all fields."""
    audience = Audience(
        name="Backend Engineers with 2-5 years Python experience",
        experience_level="intermediate",
        relevance_score=0.9,
        why_relevant=(
            "Learn modern RAG architecture patterns using FastAPI and LangGraph. "
            "Practical for building production AI systems."
        ),
    )
    assert "Backend Engineers" in audience.name
    assert audience.experience_level == "intermediate"
    assert audience.relevance_score == 0.9
    assert "RAG architecture" in audience.why_relevant


def test_audience_experience_levels():
    """Test all valid experience_level literal values."""
    for level in ["beginner", "intermediate", "advanced", "expert"]:
        audience = Audience(
            name="Test Audience",
            experience_level=level,  # type: ignore
            relevance_score=0.8,
            why_relevant="Relevant for testing purposes.",
        )
        assert audience.experience_level == level


def test_audience_invalid_experience_level():
    """Test invalid experience_level fails validation."""
    with pytest.raises(ValidationError) as exc_info:
        Audience(
            name="Test Audience",
            experience_level="novice",  # Invalid
            relevance_score=0.8,
            why_relevant="Relevant for testing.",
        )
    errors = exc_info.value.errors()
    assert any("experience_level" in str(err["loc"]) for err in errors)


def test_audience_relevance_score_bounds():
    """Test relevance_score must be between 0.0 and 1.0."""
    # Valid boundary values
    audience_min = Audience(
        name="Irrelevant Audience",
        experience_level="beginner",
        relevance_score=0.0,
        why_relevant="Not relevant at all.",
    )
    assert audience_min.relevance_score == 0.0

    audience_max = Audience(
        name="Perfect Audience",
        experience_level="expert",
        relevance_score=1.0,
        why_relevant="Perfectly aligned with content.",
    )
    assert audience_max.relevance_score == 1.0

    # Invalid values
    with pytest.raises(ValidationError) as exc_info:
        Audience(
            name="Test",
            experience_level="beginner",
            relevance_score=-0.1,
            why_relevant="Test",
        )
    errors = exc_info.value.errors()
    assert any("relevance_score" in str(err["loc"]) for err in errors)

    with pytest.raises(ValidationError) as exc_info:
        Audience(
            name="Test",
            experience_level="beginner",
            relevance_score=1.1,
            why_relevant="Test",
        )
    errors = exc_info.value.errors()
    assert any("relevance_score" in str(err["loc"]) for err in errors)


def test_audience_name_validation():
    """Test name field accepts descriptive strings."""
    audience = Audience(
        name="Frontend Developers migrating from React 18 to React 19",
        experience_level="advanced",
        relevance_score=0.85,
        why_relevant="Learn about Server Components and async transitions.",
    )
    assert "React 19" in audience.name


def test_audience_why_relevant_validation():
    """Test why_relevant field accepts explanatory strings."""
    audience = Audience(
        name="Tech Leads",
        experience_level="expert",
        relevance_score=0.9,
        why_relevant=(
            "Understand architectural tradeoffs for choosing between "
            "RAG and fine-tuning for LLM applications."
        ),
    )
    assert "tradeoffs" in audience.why_relevant


def test_audience_type_coercion():
    """Test Pydantic type coercion for relevance_score."""
    audience = Audience.model_validate(
        {
            "name": "Test Audience",
            "experience_level": "intermediate",
            "relevance_score": "0.87",  # String should convert to float
            "why_relevant": "Testing type coercion.",
        }
    )
    assert isinstance(audience.relevance_score, float)
    assert audience.relevance_score == 0.87


def test_audience_immutability():
    """Test Audience is a regular BaseModel (mutable unless frozen)."""
    audience = Audience(
        name="Test Audience",
        experience_level="beginner",
        relevance_score=0.6,
        why_relevant="Original reason.",
    )
    # BaseModel is mutable by default
    audience.relevance_score = 0.7
    assert audience.relevance_score == 0.7


# ============================================================================
# AudienceFitOutput Schema Tests (10 tests)
# ============================================================================


def test_audience_fit_output_valid_creation():
    """Test valid AudienceFitOutput creation with all fields."""
    primary = Audience(
        name="Backend Engineers with 2-5 years Python experience",
        experience_level="intermediate",
        relevance_score=0.95,
        why_relevant="Learn production RAG patterns with FastAPI.",
    )
    secondary = [
        Audience(
            name="Tech Leads evaluating RAG architectures",
            experience_level="advanced",
            relevance_score=0.8,
            why_relevant="Understand cost and performance tradeoffs.",
        )
    ]
    output = AudienceFitOutput(
        primary_audience=primary,
        secondary_audiences=secondary,
        prerequisites=[
            "Basic understanding of HTTP and REST APIs",
            "Familiarity with Python async/await syntax",
            "2+ years experience with FastAPI or similar frameworks",
        ],
        not_suitable_for=[
            "Complete beginners with no programming experience",
            "Teams using JavaScript (content is Python-specific)",
        ],
        confidence_score=0.88,
    )
    assert output.primary_audience.name.startswith("Backend Engineers")
    assert len(output.secondary_audiences) == 1
    assert len(output.prerequisites) == 3
    assert len(output.not_suitable_for) == 2
    assert output.confidence_score == 0.88


def test_audience_fit_output_secondary_audiences_default():
    """Test secondary_audiences defaults to empty list."""
    primary = Audience(
        name="General Developers",
        experience_level="intermediate",
        relevance_score=0.85,
        why_relevant="Broad appeal.",
    )
    output = AudienceFitOutput(
        primary_audience=primary,
        prerequisites=["Basic programming knowledge"],
        confidence_score=0.75,
    )
    assert output.secondary_audiences == []


def test_audience_fit_output_max_secondary_audiences():
    """Test maximum 3 secondary audiences allowed."""
    primary = Audience(
        name="Primary",
        experience_level="intermediate",
        relevance_score=0.9,
        why_relevant="Main target.",
    )
    secondary = [
        Audience(
            name=f"Secondary {i}",
            experience_level="intermediate",
            relevance_score=0.7 - (i * 0.1),
            why_relevant=f"Reason {i}",
        )
        for i in range(1, 4)  # 3 audiences
    ]

    # Valid with 3 secondary audiences
    output = AudienceFitOutput(
        primary_audience=primary,
        secondary_audiences=secondary,
        prerequisites=["Prereq 1"],
        confidence_score=0.8,
    )
    assert len(output.secondary_audiences) == 3

    # Invalid with 4 secondary audiences
    with pytest.raises(ValidationError) as exc_info:
        AudienceFitOutput(
            primary_audience=primary,
            secondary_audiences=[*secondary, secondary[0]],  # 4 audiences
            prerequisites=["Prereq 1"],
            confidence_score=0.8,
        )
    errors = exc_info.value.errors()
    assert any("secondary_audiences" in str(err["loc"]) for err in errors)


def test_audience_fit_output_prerequisites_bounds():
    """Test prerequisites must have 1-5 items."""
    primary = Audience(
        name="Test",
        experience_level="intermediate",
        relevance_score=0.8,
        why_relevant="Test",
    )

    # Valid with 1 prerequisite
    output_min = AudienceFitOutput(
        primary_audience=primary,
        prerequisites=["Prereq 1"],
        confidence_score=0.7,
    )
    assert len(output_min.prerequisites) == 1

    # Valid with 5 prerequisites
    output_max = AudienceFitOutput(
        primary_audience=primary,
        prerequisites=[f"Prereq {i}" for i in range(1, 6)],
        confidence_score=0.7,
    )
    assert len(output_max.prerequisites) == 5

    # Invalid with 0 prerequisites
    with pytest.raises(ValidationError) as exc_info:
        AudienceFitOutput(
            primary_audience=primary,
            prerequisites=[],
            confidence_score=0.7,
        )
    errors = exc_info.value.errors()
    assert any("prerequisites" in str(err["loc"]) for err in errors)

    # Invalid with 6 prerequisites
    with pytest.raises(ValidationError) as exc_info:
        AudienceFitOutput(
            primary_audience=primary,
            prerequisites=[f"Prereq {i}" for i in range(1, 7)],
            confidence_score=0.7,
        )
    errors = exc_info.value.errors()
    assert any("prerequisites" in str(err["loc"]) for err in errors)


def test_audience_fit_output_not_suitable_for_default():
    """Test not_suitable_for defaults to empty list."""
    primary = Audience(
        name="Everyone",
        experience_level="beginner",
        relevance_score=0.9,
        why_relevant="Universal appeal.",
    )
    output = AudienceFitOutput(
        primary_audience=primary,
        prerequisites=["None"],
        confidence_score=0.8,
    )
    assert output.not_suitable_for == []


def test_audience_fit_output_max_not_suitable_for():
    """Test maximum 3 not_suitable_for items."""
    primary = Audience(
        name="Test",
        experience_level="intermediate",
        relevance_score=0.8,
        why_relevant="Test",
    )

    # Valid with 3 items
    output = AudienceFitOutput(
        primary_audience=primary,
        prerequisites=["Prereq 1"],
        not_suitable_for=[f"Not for {i}" for i in range(1, 4)],
        confidence_score=0.75,
    )
    assert len(output.not_suitable_for) == 3

    # Invalid with 4 items
    with pytest.raises(ValidationError) as exc_info:
        AudienceFitOutput(
            primary_audience=primary,
            prerequisites=["Prereq 1"],
            not_suitable_for=[f"Not for {i}" for i in range(1, 5)],
            confidence_score=0.75,
        )
    errors = exc_info.value.errors()
    assert any("not_suitable_for" in str(err["loc"]) for err in errors)


def test_audience_fit_output_confidence_score_bounds():
    """Test confidence_score must be between 0.0 and 1.0."""
    primary = Audience(
        name="Test",
        experience_level="intermediate",
        relevance_score=0.8,
        why_relevant="Test",
    )

    # Valid boundary values
    output_min = AudienceFitOutput(
        primary_audience=primary,
        prerequisites=["Prereq 1"],
        confidence_score=0.0,
    )
    assert output_min.confidence_score == 0.0

    output_max = AudienceFitOutput(
        primary_audience=primary,
        prerequisites=["Prereq 1"],
        confidence_score=1.0,
    )
    assert output_max.confidence_score == 1.0

    # Invalid values
    with pytest.raises(ValidationError) as exc_info:
        AudienceFitOutput(
            primary_audience=primary,
            prerequisites=["Prereq 1"],
            confidence_score=-0.1,
        )
    errors = exc_info.value.errors()
    assert any("confidence_score" in str(err["loc"]) for err in errors)

    with pytest.raises(ValidationError) as exc_info:
        AudienceFitOutput(
            primary_audience=primary,
            prerequisites=["Prereq 1"],
            confidence_score=1.1,
        )
    errors = exc_info.value.errors()
    assert any("confidence_score" in str(err["loc"]) for err in errors)


def test_audience_fit_output_data_availability_inheritance():
    """Test AudienceFitOutput inherits DataAvailabilityMixin."""
    primary = Audience(
        name="Test",
        experience_level="intermediate",
        relevance_score=0.8,
        why_relevant="Test",
    )
    output = AudienceFitOutput(
        primary_audience=primary,
        prerequisites=["Prereq 1"],
        confidence_score=0.8,
    )
    # Default values from mixin
    assert output.data_availability == "sufficient"
    assert output.data_availability_note == ""

    # Can set explicitly
    output_limited = AudienceFitOutput(
        primary_audience=primary,
        prerequisites=["Prereq 1"],
        confidence_score=0.65,
        data_availability="limited",
        data_availability_note="Target audience not explicitly stated in content",
    )
    assert output_limited.data_availability == "limited"
    assert "not explicitly stated" in output_limited.data_availability_note


def test_audience_fit_output_type_coercion():
    """Test Pydantic type coercion for confidence_score."""
    primary = Audience(
        name="Test",
        experience_level="intermediate",
        relevance_score=0.8,
        why_relevant="Test",
    )
    output = AudienceFitOutput.model_validate(
        {
            "primary_audience": {
                "name": primary.name,
                "experience_level": primary.experience_level,
                "relevance_score": primary.relevance_score,
                "why_relevant": primary.why_relevant,
            },
            "prerequisites": ["Prereq 1"],
            "confidence_score": "0.84",  # String should convert to float
        }
    )
    assert isinstance(output.confidence_score, float)
    assert output.confidence_score == 0.84


def test_audience_fit_output_nested_validation():
    """Test nested Audience models are validated."""
    with pytest.raises(ValidationError) as exc_info:
        AudienceFitOutput.model_validate(
            {
                "primary_audience": {
                    "name": "Test",
                    "experience_level": "master",  # Invalid level
                    "relevance_score": 0.8,
                    "why_relevant": "Test",
                },
                "prerequisites": ["Prereq 1"],
                "confidence_score": 0.8,
            }
        )
    errors = exc_info.value.errors()
    assert any("experience_level" in str(err["loc"]) for err in errors)


# ============================================================================
# Action Model Tests (8 tests)
# ============================================================================


def test_action_valid_creation():
    """Test valid Action creation with all fields."""
    action = Action(
        step_number=1,
        action="Install LangGraph 0.6.7 with pip install langgraph",
        expected_outcome="LangGraph installed and importable in Python",
        time_estimate="15 minutes",
    )
    assert action.step_number == 1
    assert "LangGraph" in action.action
    assert "installed" in action.expected_outcome
    assert action.time_estimate == "15 minutes"


def test_action_step_number_validation():
    """Test step_number must be >= 1."""
    # Valid step_number
    action = Action(
        step_number=1,
        action="First step",
        expected_outcome="Outcome 1",
        time_estimate="30 minutes",
    )
    assert action.step_number == 1

    # Invalid step_number (0)
    with pytest.raises(ValidationError) as exc_info:
        Action(
            step_number=0,
            action="Invalid step",
            expected_outcome="Outcome",
            time_estimate="30 minutes",
        )
    errors = exc_info.value.errors()
    assert any("step_number" in str(err["loc"]) for err in errors)

    # Invalid step_number (negative)
    with pytest.raises(ValidationError) as exc_info:
        Action(
            step_number=-1,
            action="Invalid step",
            expected_outcome="Outcome",
            time_estimate="30 minutes",
        )
    errors = exc_info.value.errors()
    assert any("step_number" in str(err["loc"]) for err in errors)


def test_action_action_field_validation():
    """Test action field accepts imperative strings."""
    action = Action(
        step_number=1,
        action="Create FastAPI endpoint at /api/v1/analyze with async handler",
        expected_outcome="Working endpoint returning JSON",
        time_estimate="1 hour",
    )
    assert "Create" in action.action
    assert "FastAPI" in action.action


def test_action_expected_outcome_validation():
    """Test expected_outcome field accepts descriptive strings."""
    action = Action(
        step_number=2,
        action="Run pytest with coverage",
        expected_outcome=(
            "Test suite passes with 85%+ coverage, "
            "verified by coverage report showing all critical paths tested"
        ),
        time_estimate="45 minutes",
    )
    assert "85%" in action.expected_outcome


def test_action_time_estimate_examples():
    """Test time_estimate accepts various duration formats."""
    for estimate in ["15 minutes", "1 hour", "2-3 hours", "1 day", "30 minutes"]:
        action = Action(
            step_number=1,
            action="Test action",
            expected_outcome="Test outcome",
            time_estimate=estimate,
        )
        assert action.time_estimate == estimate


def test_action_type_coercion():
    """Test Pydantic type coercion for step_number."""
    action = Action.model_validate(
        {
            "step_number": "3",  # String should convert to int
            "action": "Test action",
            "expected_outcome": "Test outcome",
            "time_estimate": "1 hour",
        }
    )
    assert isinstance(action.step_number, int)
    assert action.step_number == 3


def test_action_large_step_numbers():
    """Test large step numbers are accepted."""
    action = Action(
        step_number=100,
        action="Final step in long sequence",
        expected_outcome="All steps completed",
        time_estimate="2 hours",
    )
    assert action.step_number == 100


def test_action_immutability():
    """Test Action is a regular BaseModel (mutable unless frozen)."""
    action = Action(
        step_number=1,
        action="Original action",
        expected_outcome="Original outcome",
        time_estimate="1 hour",
    )
    # BaseModel is mutable by default
    action.time_estimate = "2 hours"
    assert action.time_estimate == "2 hours"


# ============================================================================
# Resource Model Tests (7 tests)
# ============================================================================


def test_resource_valid_creation():
    """Test valid Resource creation with all fields."""
    resource = Resource(
        name="LangGraph 0.6.7 Documentation",
        url="https://langchain-ai.github.io/langgraph/",
        resource_type="documentation",
        relevance="Essential for understanding state persistence in multi-agent workflows",
    )
    assert "LangGraph" in resource.name
    assert resource.url == "https://langchain-ai.github.io/langgraph/"
    assert resource.resource_type == "documentation"
    assert "state persistence" in resource.relevance


def test_resource_url_optional():
    """Test url field defaults to None."""
    resource = Resource(
        name="Internal tool mentioned in content",
        resource_type="tool",
        relevance="Useful for deployment",
    )
    assert resource.url is None


def test_resource_url_explicit_none():
    """Test url can be explicitly set to None."""
    resource = Resource(
        name="Proprietary library",
        url=None,
        resource_type="library",
        relevance="Referenced but no public URL available",
    )
    assert resource.url is None


def test_resource_type_values():
    """Test all valid resource_type literal values."""
    for res_type in ["documentation", "tutorial", "tool", "library", "course"]:
        resource = Resource(
            name="Test Resource",
            resource_type=res_type,  # type: ignore
            relevance="Testing resource types",
        )
        assert resource.resource_type == res_type


def test_resource_invalid_type():
    """Test invalid resource_type fails validation."""
    with pytest.raises(ValidationError) as exc_info:
        Resource(
            name="Test",
            resource_type="blog",  # Invalid type
            relevance="Test",
        )
    errors = exc_info.value.errors()
    assert any("resource_type" in str(err["loc"]) for err in errors)


def test_resource_relevance_validation():
    """Test relevance field accepts explanatory strings."""
    resource = Resource(
        name="FastAPI Tutorial - Async Operations",
        url="https://fastapi.tiangolo.com/async/",
        resource_type="tutorial",
        relevance=(
            "Provides benchmarks for comparing HNSW vs IVF indexing performance "
            "in production RAG systems"
        ),
    )
    assert "benchmarks" in resource.relevance


def test_resource_immutability():
    """Test Resource is a regular BaseModel (mutable unless frozen)."""
    resource = Resource(
        name="Test Resource",
        resource_type="documentation",
        relevance="Original relevance",
    )
    # BaseModel is mutable by default
    resource.relevance = "Updated relevance"
    assert resource.relevance == "Updated relevance"


# ============================================================================
# ActionableOutput Schema Tests (12 tests)
# ============================================================================


def test_actionable_output_valid_creation():
    """Test valid ActionableOutput creation with all fields."""
    immediate = [
        Action(
            step_number=1,
            action="Install LangGraph 0.6.7",
            expected_outcome="LangGraph installed",
            time_estimate="15 minutes",
        ),
        Action(
            step_number=2,
            action="Run hello-world example",
            expected_outcome="State persistence working",
            time_estimate="30 minutes",
        ),
    ]
    follow_up = [
        Action(
            step_number=3,
            action="Build multi-agent workflow",
            expected_outcome="Working agent coordination",
            time_estimate="2 days",
        )
    ]
    resources = [
        Resource(
            name="LangGraph Docs",
            url="https://langchain-ai.github.io/langgraph/",
            resource_type="documentation",
            relevance="Core reference",
        )
    ]
    output = ActionableOutput(
        immediate_actions=immediate,
        follow_up_actions=follow_up,
        resources=resources,
        quick_win=(
            "Install LangGraph 0.6.7 and run the hello-world example to see "
            "state persistence in action - takes 15 minutes and validates "
            "your environment is ready"
        ),
        confidence_score=0.9,
    )
    assert len(output.immediate_actions) == 2
    assert len(output.follow_up_actions) == 1
    assert len(output.resources) == 1
    assert "15 minutes" in output.quick_win
    assert output.confidence_score == 0.9


def test_actionable_output_min_immediate_actions():
    """Test minimum 1 immediate action required."""
    # Valid with 1 action
    output = ActionableOutput(
        immediate_actions=[
            Action(
                step_number=1,
                action="First action",
                expected_outcome="Outcome 1",
                time_estimate="30 minutes",
            )
        ],
        quick_win="Quick win description here",
        confidence_score=0.8,
    )
    assert len(output.immediate_actions) == 1

    # Invalid with 0 actions
    with pytest.raises(ValidationError) as exc_info:
        ActionableOutput(
            immediate_actions=[],
            quick_win="Quick win",
            confidence_score=0.8,
        )
    errors = exc_info.value.errors()
    assert any("immediate_actions" in str(err["loc"]) for err in errors)


def test_actionable_output_max_immediate_actions():
    """Test maximum 3 immediate actions allowed."""
    actions = [
        Action(
            step_number=i,
            action=f"Action {i}",
            expected_outcome=f"Outcome {i}",
            time_estimate="30 minutes",
        )
        for i in range(1, 4)
    ]

    # Valid with 3 actions
    output = ActionableOutput(
        immediate_actions=actions,
        quick_win="Quick win",
        confidence_score=0.8,
    )
    assert len(output.immediate_actions) == 3

    # Invalid with 4 actions
    with pytest.raises(ValidationError) as exc_info:
        ActionableOutput(
            immediate_actions=[*actions, actions[0]],
            quick_win="Quick win",
            confidence_score=0.8,
        )
    errors = exc_info.value.errors()
    assert any("immediate_actions" in str(err["loc"]) for err in errors)


def test_actionable_output_follow_up_actions_default():
    """Test follow_up_actions defaults to empty list."""
    output = ActionableOutput(
        immediate_actions=[
            Action(
                step_number=1,
                action="First action",
                expected_outcome="Outcome",
                time_estimate="30 minutes",
            )
        ],
        quick_win="Quick win",
        confidence_score=0.8,
    )
    assert output.follow_up_actions == []


def test_actionable_output_max_follow_up_actions():
    """Test maximum 5 follow-up actions allowed."""
    immediate = [
        Action(
            step_number=1,
            action="Immediate",
            expected_outcome="Done",
            time_estimate="30 minutes",
        )
    ]
    follow_up = [
        Action(
            step_number=i,
            action=f"Follow-up {i}",
            expected_outcome=f"Outcome {i}",
            time_estimate="1 day",
        )
        for i in range(2, 7)  # 5 actions
    ]

    # Valid with 5 follow-up actions
    output = ActionableOutput(
        immediate_actions=immediate,
        follow_up_actions=follow_up,
        quick_win="Quick win",
        confidence_score=0.8,
    )
    assert len(output.follow_up_actions) == 5

    # Invalid with 6 follow-up actions
    with pytest.raises(ValidationError) as exc_info:
        ActionableOutput(
            immediate_actions=immediate,
            follow_up_actions=[*follow_up, follow_up[0]],
            quick_win="Quick win",
            confidence_score=0.8,
        )
    errors = exc_info.value.errors()
    assert any("follow_up_actions" in str(err["loc"]) for err in errors)


def test_actionable_output_resources_default():
    """Test resources defaults to empty list."""
    output = ActionableOutput(
        immediate_actions=[
            Action(
                step_number=1,
                action="Action",
                expected_outcome="Outcome",
                time_estimate="30 minutes",
            )
        ],
        quick_win="Quick win",
        confidence_score=0.8,
    )
    assert output.resources == []


def test_actionable_output_max_resources():
    """Test maximum 5 resources allowed."""
    immediate = [
        Action(
            step_number=1,
            action="Action",
            expected_outcome="Outcome",
            time_estimate="30 minutes",
        )
    ]
    resources = [
        Resource(
            name=f"Resource {i}",
            resource_type="documentation",
            relevance=f"Relevance {i}",
        )
        for i in range(1, 6)  # 5 resources
    ]

    # Valid with 5 resources
    output = ActionableOutput(
        immediate_actions=immediate,
        resources=resources,
        quick_win="Quick win",
        confidence_score=0.8,
    )
    assert len(output.resources) == 5

    # Invalid with 6 resources
    with pytest.raises(ValidationError) as exc_info:
        ActionableOutput(
            immediate_actions=immediate,
            resources=[*resources, resources[0]],
            quick_win="Quick win",
            confidence_score=0.8,
        )
    errors = exc_info.value.errors()
    assert any("resources" in str(err["loc"]) for err in errors)


def test_actionable_output_quick_win_validation():
    """Test quick_win field accepts complete sentences."""
    output = ActionableOutput(
        immediate_actions=[
            Action(
                step_number=1,
                action="Action",
                expected_outcome="Outcome",
                time_estimate="30 minutes",
            )
        ],
        quick_win=(
            "Install LangGraph 0.6.7 and run the hello-world example to see "
            "state persistence in action - takes 15 minutes and validates "
            "your environment is ready"
        ),
        confidence_score=0.85,
    )
    assert len(output.quick_win) > 50


def test_actionable_output_confidence_score_bounds():
    """Test confidence_score must be between 0.0 and 1.0."""
    immediate = [
        Action(
            step_number=1,
            action="Action",
            expected_outcome="Outcome",
            time_estimate="30 minutes",
        )
    ]

    # Valid boundary values
    output_min = ActionableOutput(
        immediate_actions=immediate,
        quick_win="Quick win",
        confidence_score=0.0,
    )
    assert output_min.confidence_score == 0.0

    output_max = ActionableOutput(
        immediate_actions=immediate,
        quick_win="Quick win",
        confidence_score=1.0,
    )
    assert output_max.confidence_score == 1.0

    # Invalid values
    with pytest.raises(ValidationError) as exc_info:
        ActionableOutput(
            immediate_actions=immediate,
            quick_win="Quick win",
            confidence_score=-0.1,
        )
    errors = exc_info.value.errors()
    assert any("confidence_score" in str(err["loc"]) for err in errors)

    with pytest.raises(ValidationError) as exc_info:
        ActionableOutput(
            immediate_actions=immediate,
            quick_win="Quick win",
            confidence_score=1.1,
        )
    errors = exc_info.value.errors()
    assert any("confidence_score" in str(err["loc"]) for err in errors)


def test_actionable_output_data_availability_inheritance():
    """Test ActionableOutput inherits DataAvailabilityMixin."""
    output = ActionableOutput(
        immediate_actions=[
            Action(
                step_number=1,
                action="Action",
                expected_outcome="Outcome",
                time_estimate="30 minutes",
            )
        ],
        quick_win="Quick win",
        confidence_score=0.8,
    )
    # Default values from mixin
    assert output.data_availability == "sufficient"
    assert output.data_availability_note == ""

    # Can set explicitly
    output_limited = ActionableOutput(
        immediate_actions=[
            Action(
                step_number=1,
                action="Action",
                expected_outcome="Outcome",
                time_estimate="30 minutes",
            )
        ],
        quick_win="Quick win",
        confidence_score=0.65,
        data_availability="limited",
        data_availability_note="Only high-level steps mentioned, no detailed instructions",
    )
    assert output_limited.data_availability == "limited"
    assert "no detailed instructions" in output_limited.data_availability_note


def test_actionable_output_type_coercion():
    """Test Pydantic type coercion for confidence_score."""
    output = ActionableOutput.model_validate(
        {
            "immediate_actions": [
                {
                    "step_number": 1,
                    "action": "Action",
                    "expected_outcome": "Outcome",
                    "time_estimate": "30 minutes",
                }
            ],
            "quick_win": "Quick win",
            "confidence_score": "0.86",  # String should convert to float
        }
    )
    assert isinstance(output.confidence_score, float)
    assert output.confidence_score == 0.86


def test_actionable_output_nested_validation():
    """Test nested Action and Resource models are validated."""
    with pytest.raises(ValidationError) as exc_info:
        ActionableOutput.model_validate(
            {
                "immediate_actions": [
                    {
                        "step_number": 0,  # Invalid - must be >= 1
                        "action": "Action",
                        "expected_outcome": "Outcome",
                        "time_estimate": "30 minutes",
                    }
                ],
                "quick_win": "Quick win",
                "confidence_score": 0.8,
            }
        )
    errors = exc_info.value.errors()
    assert any("step_number" in str(err["loc"]) for err in errors)
