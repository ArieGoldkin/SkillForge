"""Unit tests for Tier 3 Research Agent schemas.

Tests for the 4 research agents that run in Deep Dive mode:
- DeepResearcherOutput: Extended web research with synthesized findings
- CommunityPulseOutput: Sentiment analysis from community sources
- KnowledgeCuratorOutput: Knowledge graph connections to user's library
- LearningPathAdvisorOutput: Personalized learning paths

Issue #501: Tier 3 Research Agents implementation.
"""

import pytest
from pydantic import ValidationError

from app.domains.analysis.schemas.agents.community_pulse import (
    CommunityConcern,
    CommunityPulseOutput,
    Discussion,
    GitHubMetrics,
)
from app.domains.analysis.schemas.agents.deep_researcher import (
    DeepResearcherOutput,
    ResearchFinding,
)
from app.domains.analysis.schemas.agents.knowledge_curator import (
    KnowledgeConnection,
    KnowledgeCuratorOutput,
    RecommendedContent,
)
from app.domains.analysis.schemas.agents.learning_path_advisor import (
    LearningPathAdvisorOutput,
    LearningStep,
    SkillGap,
)

# ============================================================================
# DeepResearcherOutput Tests
# ============================================================================


class TestResearchFinding:
    """Tests for ResearchFinding model."""

    def test_valid_finding(self):
        """Test valid ResearchFinding creation."""
        finding = ResearchFinding(
            topic="Vector Database Performance",
            summary="HNSW indexing provides 10x faster queries than brute force. This is documented across multiple benchmarks.",
            sources=["https://arxiv.org/paper1", "https://docs.pinecone.io"],
            confidence=0.9,
        )
        assert finding.topic == "Vector Database Performance"
        assert len(finding.sources) == 2
        assert finding.confidence == 0.9

    def test_finding_confidence_bounds(self):
        """Test confidence must be between 0.0 and 1.0."""
        # Valid bounds
        ResearchFinding(
            topic="Test",
            summary="Summary text.",
            sources=["https://example.com"],
            confidence=0.0,
        )
        ResearchFinding(
            topic="Test",
            summary="Summary text.",
            sources=["https://example.com"],
            confidence=1.0,
        )

        # Invalid bounds
        with pytest.raises(ValidationError):
            ResearchFinding(
                topic="Test",
                summary="Summary",
                sources=["https://example.com"],
                confidence=1.5,
            )

    def test_finding_requires_sources(self):
        """Test finding requires at least one source."""
        with pytest.raises(ValidationError):
            ResearchFinding(
                topic="Test",
                summary="Summary text.",
                sources=[],  # Empty sources
                confidence=0.8,
            )


class TestDeepResearcherOutput:
    """Tests for DeepResearcherOutput model."""

    def test_valid_output(self):
        """Test valid DeepResearcherOutput creation."""
        output = DeepResearcherOutput(
            research_findings=[
                ResearchFinding(
                    topic="LangGraph Checkpointing",
                    summary="PostgresSaver enables persistent workflow state across restarts.",
                    sources=["https://langchain.dev"],
                    confidence=0.9,
                )
            ],
            knowledge_gaps=["Memory patterns for proactive recall need more research"],
            source_quality_assessment="Sources are from official documentation and recent blog posts. High credibility.",
            search_queries_used=["LangGraph checkpointing", "LangGraph state persistence"],
            summary="LangGraph provides robust checkpointing for production workflows.",
            confidence_score=0.85,
        )
        assert len(output.research_findings) == 1
        assert len(output.knowledge_gaps) == 1
        assert output.confidence_score == 0.85

    def test_output_with_data_availability(self):
        """Test data availability mixin fields."""
        output = DeepResearcherOutput(
            research_findings=[],
            knowledge_gaps=["Unable to find reliable sources"],
            source_quality_assessment="Limited sources found for this topic.",
            search_queries_used=["test query"],
            summary="Limited research available on this topic.",
            confidence_score=0.3,
            data_availability="limited",
            data_availability_note="Only found 1 primary source.",
        )
        assert output.data_availability == "limited"
        assert output.data_availability_note == "Only found 1 primary source."

    def test_output_empty_findings(self):
        """Test output with no findings (valid case)."""
        output = DeepResearcherOutput(
            research_findings=[],
            knowledge_gaps=[],
            source_quality_assessment="No relevant sources found.",
            search_queries_used=[],
            summary="No research findings available.",
            confidence_score=0.1,
        )
        assert len(output.research_findings) == 0


# ============================================================================
# CommunityPulseOutput Tests
# ============================================================================


class TestCommunityConcern:
    """Tests for CommunityConcern model."""

    def test_valid_concern(self):
        """Test valid CommunityConcern creation."""
        concern = CommunityConcern(
            issue="Learning curve is steep for beginners",
            frequency="common",
            severity="medium",
        )
        assert concern.issue == "Learning curve is steep for beginners"
        assert concern.frequency == "common"
        assert concern.severity == "medium"

    def test_frequency_values(self):
        """Test all valid frequency values."""
        for frequency in ["rare", "occasional", "common", "widespread"]:
            concern = CommunityConcern(
                issue="Test issue",
                frequency=frequency,
                severity="low",
            )
            assert concern.frequency == frequency

    def test_severity_values(self):
        """Test all valid severity values."""
        for severity in ["low", "medium", "high", "critical"]:
            concern = CommunityConcern(
                issue="Test issue",
                frequency="occasional",
                severity=severity,
            )
            assert concern.severity == severity


class TestDiscussion:
    """Tests for Discussion model."""

    def test_valid_discussion(self):
        """Test valid Discussion creation."""
        discussion = Discussion(
            source="HackerNews",
            title="Why we switched from LangChain to LangGraph",
            url="https://news.ycombinator.com/item?id=12345",
            sentiment="positive",
        )
        assert discussion.source == "HackerNews"
        assert discussion.sentiment == "positive"

    def test_discussion_sentiment_values(self):
        """Test valid sentiment values."""
        for sentiment in ["positive", "negative", "neutral", "mixed"]:
            discussion = Discussion(
                source="Reddit",
                title="Test discussion",
                url="https://reddit.com/r/test",
                sentiment=sentiment,
            )
            assert discussion.sentiment == sentiment


class TestGitHubMetrics:
    """Tests for GitHubMetrics model."""

    def test_valid_metrics(self):
        """Test valid GitHubMetrics creation."""
        metrics = GitHubMetrics(
            stars_trend="increasing",
            issues_open=150,
            pr_velocity="high",
        )
        assert metrics.stars_trend == "increasing"
        assert metrics.issues_open == 150
        assert metrics.pr_velocity == "high"

    def test_stars_trend_values(self):
        """Test all valid stars_trend values."""
        for trend in ["increasing", "stable", "decreasing"]:
            metrics = GitHubMetrics(
                stars_trend=trend,
                issues_open=10,
                pr_velocity="moderate",
            )
            assert metrics.stars_trend == trend

    def test_pr_velocity_values(self):
        """Test all valid pr_velocity values."""
        for velocity in ["low", "moderate", "high"]:
            metrics = GitHubMetrics(
                stars_trend="stable",
                issues_open=10,
                pr_velocity=velocity,
            )
            assert metrics.pr_velocity == velocity

    def test_issues_open_non_negative(self):
        """Test issues_open cannot be negative."""
        with pytest.raises(ValidationError):
            GitHubMetrics(
                stars_trend="stable",
                issues_open=-1,
                pr_velocity="moderate",
            )


class TestCommunityPulseOutput:
    """Tests for CommunityPulseOutput model."""

    def test_valid_output(self):
        """Test valid CommunityPulseOutput creation."""
        output = CommunityPulseOutput(
            adoption_trend="rising",
            sentiment_score=0.7,
            community_concerns=[
                CommunityConcern(
                    issue="Learning curve",
                    frequency="common",
                    severity="medium",
                )
            ],
            notable_discussions=[
                Discussion(
                    source="Reddit",
                    title="LangGraph production experience",
                    url="https://reddit.com/r/langchain",
                    sentiment="positive",
                )
            ],
            github_activity=GitHubMetrics(
                stars_trend="increasing",
                issues_open=100,
                pr_velocity="high",
            ),
            summary="Growing community with positive sentiment.",
            confidence_score=0.8,
        )
        assert output.sentiment_score == 0.7
        assert len(output.community_concerns) == 1
        assert output.github_activity is not None

    def test_adoption_trend_values(self):
        """Test all valid adoption_trend values."""
        for trend in ["rising", "stable", "declining", "emerging"]:
            output = CommunityPulseOutput(
                adoption_trend=trend,
                sentiment_score=0.0,
                community_concerns=[],
                notable_discussions=[],
                summary="Test summary.",
                confidence_score=0.5,
            )
            assert output.adoption_trend == trend

    def test_sentiment_score_bounds(self):
        """Test sentiment_score must be between -1.0 and 1.0."""
        # Valid bounds
        CommunityPulseOutput(
            adoption_trend="stable",
            sentiment_score=-1.0,
            community_concerns=[],
            notable_discussions=[],
            summary="Test",
            confidence_score=0.5,
        )
        CommunityPulseOutput(
            adoption_trend="stable",
            sentiment_score=1.0,
            community_concerns=[],
            notable_discussions=[],
            summary="Test",
            confidence_score=0.5,
        )

        # Invalid bounds
        with pytest.raises(ValidationError):
            CommunityPulseOutput(
                adoption_trend="stable",
                sentiment_score=1.5,
                community_concerns=[],
                notable_discussions=[],
                summary="Test",
                confidence_score=0.5,
            )

    def test_output_without_github_metrics(self):
        """Test output without GitHub metrics (optional field)."""
        output = CommunityPulseOutput(
            adoption_trend="stable",
            sentiment_score=0.0,
            community_concerns=[],
            notable_discussions=[],
            github_activity=None,  # Explicitly None
            summary="No GitHub project.",
            confidence_score=0.5,
        )
        assert output.github_activity is None


# ============================================================================
# KnowledgeCuratorOutput Tests
# ============================================================================


class TestKnowledgeConnection:
    """Tests for KnowledgeConnection model."""

    def test_valid_connection(self):
        """Test valid KnowledgeConnection creation."""
        connection = KnowledgeConnection(
            related_analysis_id="abc-123",
            relationship_type="builds_upon",
            relevance=0.8,
        )
        assert connection.relationship_type == "builds_upon"
        assert connection.relevance == 0.8

    def test_relationship_types(self):
        """Test valid relationship_type values."""
        for rel_type in [
            "prerequisite",
            "builds_upon",
            "alternative",
            "complementary",
            "contradicts",
            "extends",
        ]:
            connection = KnowledgeConnection(
                related_analysis_id="test-id",
                relationship_type=rel_type,
                relevance=0.5,
            )
            assert connection.relationship_type == rel_type

    def test_relevance_bounds(self):
        """Test relevance must be between 0.0 and 1.0."""
        KnowledgeConnection(
            related_analysis_id="test-id",
            relationship_type="prerequisite",
            relevance=0.0,
        )
        KnowledgeConnection(
            related_analysis_id="test-id",
            relationship_type="prerequisite",
            relevance=1.0,
        )
        with pytest.raises(ValidationError):
            KnowledgeConnection(
                related_analysis_id="test-id",
                relationship_type="prerequisite",
                relevance=1.5,
            )


class TestRecommendedContent:
    """Tests for RecommendedContent model."""

    def test_valid_recommendation(self):
        """Test valid RecommendedContent creation."""
        rec = RecommendedContent(
            title="Advanced RAG Patterns",
            reason="Builds on the vector search concepts from this content.",
            priority="high",
        )
        assert rec.title == "Advanced RAG Patterns"
        assert rec.priority == "high"

    def test_priority_values(self):
        """Test all valid priority values."""
        for priority in ["low", "medium", "high"]:
            rec = RecommendedContent(
                title="Test Content",
                reason="Test reason.",
                priority=priority,
            )
            assert rec.priority == priority


class TestKnowledgeCuratorOutput:
    """Tests for KnowledgeCuratorOutput model."""

    def test_valid_output(self):
        """Test valid KnowledgeCuratorOutput creation."""
        output = KnowledgeCuratorOutput(
            connections=[
                KnowledgeConnection(
                    related_analysis_id="prev-123",
                    relationship_type="prerequisite",
                    relevance=0.9,
                )
            ],
            prerequisites=["Understanding of embeddings", "Basic SQL knowledge"],
            builds_upon=["Vector database fundamentals"],
            recommended_next=[
                RecommendedContent(
                    title="Advanced RAG",
                    reason="Next step in learning path.",
                    priority="high",
                )
            ],
            knowledge_graph_position="Intermediate level content on RAG. Connects to 3 existing items.",
            summary="Connects well to existing knowledge base with strong prerequisites.",
            confidence_score=0.85,
        )
        assert len(output.connections) == 1
        assert len(output.prerequisites) == 2

    def test_empty_connections(self):
        """Test output with no connections (new topic area)."""
        output = KnowledgeCuratorOutput(
            connections=[],
            prerequisites=[],
            builds_upon=[],
            recommended_next=[],
            knowledge_graph_position="New topic area - no existing connections.",
            summary="No prior analyses found for this topic.",
            confidence_score=0.7,
            data_availability="limited",
            data_availability_note="No prior analyses found for connection.",
        )
        assert output.data_availability == "limited"


# ============================================================================
# LearningPathAdvisorOutput Tests
# ============================================================================


class TestLearningStep:
    """Tests for LearningStep model."""

    def test_valid_step(self):
        """Test valid LearningStep creation."""
        step = LearningStep(
            step_number=1,
            title="Understand Vector Embeddings",
            description="Learn how text is converted to vectors for semantic search.",
            estimated_time="2 hours",
            prerequisites=["Basic Python knowledge"],
            difficulty="beginner",
        )
        assert step.step_number == 1
        assert step.estimated_time == "2 hours"
        assert step.difficulty == "beginner"

    def test_step_number_must_be_positive(self):
        """Test step_number must be >= 1."""
        with pytest.raises(ValidationError):
            LearningStep(
                step_number=0,
                title="Invalid Step",
                description="This should fail.",
                estimated_time="1 hour",
                prerequisites=[],
                difficulty="beginner",
            )

    def test_difficulty_values(self):
        """Test all valid difficulty values."""
        for difficulty in ["beginner", "intermediate", "advanced"]:
            step = LearningStep(
                step_number=1,
                title="Test Step",
                description="Description.",
                estimated_time="1 hour",
                prerequisites=[],
                difficulty=difficulty,
            )
            assert step.difficulty == difficulty


class TestSkillGap:
    """Tests for SkillGap model."""

    def test_valid_skill_gap(self):
        """Test valid SkillGap creation."""
        gap = SkillGap(
            skill_name="Database Indexing",
            importance="critical",
            recommended_resource="https://docs.postgresql.org/indexes",
        )
        assert gap.skill_name == "Database Indexing"
        assert gap.importance == "critical"

    def test_importance_values(self):
        """Test valid importance values."""
        for importance in ["critical", "important", "nice-to-have"]:
            gap = SkillGap(
                skill_name="Test Skill",
                importance=importance,
            )
            assert gap.importance == importance

    def test_optional_resource(self):
        """Test skill gap without recommended resource."""
        gap = SkillGap(
            skill_name="Advanced SQL",
            importance="important",
            recommended_resource=None,
        )
        assert gap.recommended_resource is None


class TestLearningPathAdvisorOutput:
    """Tests for LearningPathAdvisorOutput model."""

    def test_valid_output(self):
        """Test valid LearningPathAdvisorOutput creation."""
        output = LearningPathAdvisorOutput(
            learning_path=[
                LearningStep(
                    step_number=1,
                    title="Start Here",
                    description="Begin with fundamentals of the topic.",
                    estimated_time="1 hour",
                    prerequisites=[],
                    difficulty="beginner",
                ),
                LearningStep(
                    step_number=2,
                    title="Intermediate Concepts",
                    description="Build on basics with practical examples.",
                    estimated_time="2 hours",
                    prerequisites=["Step 1 concepts"],
                    difficulty="intermediate",
                ),
                LearningStep(
                    step_number=3,
                    title="Advanced Topics",
                    description="Deep dive into advanced patterns.",
                    estimated_time="3 hours",
                    prerequisites=["Step 2 concepts"],
                    difficulty="advanced",
                ),
            ],
            skill_gaps=[
                SkillGap(
                    skill_name="State Management",
                    importance="critical",
                )
            ],
            personalization_summary="Path tailored for intermediate Python developers with focus on practical skills.",
            estimated_total_time="6 hours",
            confidence_score=0.9,
        )
        assert len(output.learning_path) == 3
        assert output.estimated_total_time == "6 hours"

    def test_learning_path_min_length(self):
        """Test learning path requires minimum 3 steps."""
        with pytest.raises(ValidationError):
            LearningPathAdvisorOutput(
                learning_path=[
                    LearningStep(
                        step_number=1,
                        title="Only Step",
                        description="Too short.",
                        estimated_time="1 hour",
                        prerequisites=[],
                        difficulty="beginner",
                    )
                ],
                skill_gaps=[],
                personalization_summary="Too few steps.",
                estimated_total_time="1 hour",
                confidence_score=0.5,
            )

    def test_learning_path_max_length(self):
        """Test learning path allows maximum 8 steps."""
        steps = [
            LearningStep(
                step_number=i,
                title=f"Step {i}",
                description=f"Description for step {i}.",
                estimated_time="1 hour",
                prerequisites=[],
                difficulty="beginner",
            )
            for i in range(1, 9)  # 8 steps
        ]
        output = LearningPathAdvisorOutput(
            learning_path=steps,
            skill_gaps=[],
            personalization_summary="Maximum steps.",
            estimated_total_time="8 hours",
            confidence_score=0.8,
        )
        assert len(output.learning_path) == 8

    def test_learning_path_exceeds_max_length(self):
        """Test learning path rejects more than 8 steps."""
        steps = [
            LearningStep(
                step_number=i,
                title=f"Step {i}",
                description=f"Description for step {i}.",
                estimated_time="1 hour",
                prerequisites=[],
                difficulty="beginner",
            )
            for i in range(1, 11)  # 10 steps - too many
        ]
        with pytest.raises(ValidationError):
            LearningPathAdvisorOutput(
                learning_path=steps,
                skill_gaps=[],
                personalization_summary="Too many steps.",
                estimated_total_time="10 hours",
                confidence_score=0.8,
            )

    def test_output_with_data_availability(self):
        """Test output when user memory is limited."""
        output = LearningPathAdvisorOutput(
            learning_path=[
                LearningStep(
                    step_number=i,
                    title=f"Step {i}",
                    description=f"Generic step {i}.",
                    estimated_time="1 hour",
                    prerequisites=[],
                    difficulty="beginner",
                )
                for i in range(1, 4)  # 3 steps
            ],
            skill_gaps=[],
            personalization_summary="Generic path - no user preferences available.",
            estimated_total_time="3 hours",
            confidence_score=0.4,
            data_availability="limited",
            data_availability_note="No user preference data available.",
        )
        assert output.data_availability == "limited"


# ============================================================================
# Integration Tests
# ============================================================================


class TestTier3SchemaImports:
    """Test all Tier 3 schemas can be imported."""

    def test_all_imports_successful(self):
        """Verify all Tier 3 schema classes are importable."""
        from app.domains.analysis.schemas.agents import (
            CommunityPulseOutput,
            DeepResearcherOutput,
            KnowledgeCuratorOutput,
            LearningPathAdvisorOutput,
        )

        assert DeepResearcherOutput is not None
        assert CommunityPulseOutput is not None
        assert KnowledgeCuratorOutput is not None
        assert LearningPathAdvisorOutput is not None

    def test_nested_model_imports(self):
        """Verify nested models are importable."""
        from app.domains.analysis.schemas.agents.community_pulse import (
            CommunityConcern,
            Discussion,
            GitHubMetrics,
        )
        from app.domains.analysis.schemas.agents.deep_researcher import ResearchFinding
        from app.domains.analysis.schemas.agents.knowledge_curator import (
            KnowledgeConnection,
            RecommendedContent,
        )
        from app.domains.analysis.schemas.agents.learning_path_advisor import (
            LearningStep,
            SkillGap,
        )

        assert ResearchFinding is not None
        assert CommunityConcern is not None
        assert Discussion is not None
        assert GitHubMetrics is not None
        assert KnowledgeConnection is not None
        assert RecommendedContent is not None
        assert LearningStep is not None
        assert SkillGap is not None
