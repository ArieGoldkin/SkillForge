"""Unit tests for synthesis LLM functions."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.types import AnalysisID
from app.workflows.tasks.aggregation.synthesis import (
    create_fallback_synthesis_model,
    create_synthesis_agent,
    create_synthesis_agent_with_fallback,
    synthesize_with_llm,
)
from app.workflows.tasks.schemas.aggregated_insights import AggregatedInsights


@pytest.fixture
def sample_analysis_id() -> str:
    """Sample analysis ID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_validated_findings() -> list[dict[str, object]]:
    """Sample validated agent findings."""
    return [
        {
            "agent_type": "tech_comparator",
            "findings": {
                "primary_tech": "LangGraph",
                "alternatives": ["LangChain Agents"],
                "recommendation": "Use LangGraph for state management",
                "confidence_score": 0.85,
            },
        },
        {
            "agent_type": "security_auditor",
            "findings": {
                "security_risks": [
                    {
                        "risk_type": "authentication",
                        "severity": "high",
                        "description": "Missing API authentication",
                        "mitigation": "Implement JWT tokens",
                    }
                ],
                "recommendation": "Address high-severity risks first",
                "confidence_score": 0.88,
            },
        },
    ]


@pytest.fixture
def sample_conflicts() -> list[dict[str, str]]:
    """Sample detected conflicts."""
    return [
        {
            "agent_1": "tech_comparator",
            "agent_2": "security_auditor",
            "conflict": "tech_comparator recommends adoption, security_auditor raises security concerns",
        }
    ]


@pytest.fixture
def sample_confidence_scores() -> dict[str, float]:
    """Sample confidence scores."""
    return {
        "tech_comparator": 0.85,
        "security_auditor": 0.88,
    }


@pytest.fixture
def sample_llm_response() -> dict[str, object]:
    """Sample LLM synthesis response."""
    return {
        "executive_summary": (
            "LangGraph provides powerful state management for workflows. "
            "Security authentication must be implemented before production deployment. "
            "The technology is mature but requires careful security configuration."
        ),
        "key_findings": [
            "LangGraph offers superior state management compared to alternatives",
            "High-severity authentication gap requires immediate attention",
            "Implementation feasible with proper security controls",
        ],
        "synthesis": {
            "technical_analysis": "LangGraph provides graph-based workflow capabilities...",
            "implementation_guidance": "1. Install LangGraph\n2. Implement authentication\n3. Configure security",
            "risk_assessment": "- High: Missing authentication\n- Medium: Integration complexity",
            "recommendations": "- Implement JWT authentication\n- Use LangGraph for workflows",
        },
        "conflicts_resolved": [
            {
                "conflict": "tech_comparator recommends adoption, security_auditor raises concerns",
                "resolution": "Adopt LangGraph with mandatory security controls",
                "priority_agent": "security_auditor",
                "reasoning": "Security concerns must be addressed before technology adoption",
            }
        ],
        "coverage_gaps": [],
        "cross_domain_connections": [
            {
                "domains": ["technology", "security"],
                "connection": "Technology adoption requires security implementation",
                "agents_involved": ["tech_comparator", "security_auditor"],
            }
        ],
        "coverage_score": 0.25,
    }


class TestCreateSynthesisAgent:
    """Test synthesis agent creation."""

    @patch("app.workflows.tasks.aggregation.synthesis.create_structured_agent")
    def test_create_synthesis_agent_calls_create_structured_agent(
        self, mock_create_structured_agent: MagicMock
    ):
        """Test that create_synthesis_agent calls create_structured_agent with correct args."""
        mock_agent = MagicMock()
        mock_create_structured_agent.return_value = mock_agent

        # Import and call the actual function (don't mock it)
        result = create_synthesis_agent()

        # Verify create_structured_agent was called
        mock_create_structured_agent.assert_called_once()
        call_kwargs = mock_create_structured_agent.call_args.kwargs

        # Verify system_prompt was passed
        # Issue #304: Prompt redesigned for triple-purpose artifacts
        assert "system_prompt" in call_kwargs
        system_prompt_lower = call_kwargs["system_prompt"].lower()
        assert "triple-purpose" in system_prompt_lower
        assert "executive_summary" in system_prompt_lower  # Required section

        # Verify response_schema is AggregatedInsights
        assert "response_schema" in call_kwargs
        assert call_kwargs["response_schema"] == AggregatedInsights

        # Verify result is the mock agent
        assert result == mock_agent

    @patch("app.workflows.tasks.aggregation.synthesis.create_structured_agent")
    def test_create_synthesis_agent_returns_runnable(self, mock_create_structured_agent: MagicMock):
        """Test that create_synthesis_agent returns a Runnable."""
        mock_agent = MagicMock()
        mock_create_structured_agent.return_value = mock_agent

        result = create_synthesis_agent()

        # Verify result is returned
        assert result is not None
        assert result == mock_agent


class TestCreateFallbackSynthesisModel:
    """Test fallback synthesis model creation (Issue #299-304)."""

    @patch("app.workflows.tasks.aggregation.synthesis.get_chat_model")
    def test_create_fallback_synthesis_model_uses_fallback_setting(
        self, mock_get_chat_model: MagicMock
    ):
        """Test that fallback model uses LLM_FALLBACK_MODEL setting."""
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = MagicMock()
        mock_get_chat_model.return_value = mock_model

        result = create_fallback_synthesis_model()

        # Verify get_chat_model was called with fallback model config
        mock_get_chat_model.assert_called_once()
        call_kwargs = mock_get_chat_model.call_args.kwargs
        assert "config" in call_kwargs
        assert "configurable" in call_kwargs["config"]
        assert "model" in call_kwargs["config"]["configurable"]

        # Verify structured output is bound
        mock_model.with_structured_output.assert_called_once_with(AggregatedInsights)

        assert result is not None

    @patch("app.workflows.tasks.aggregation.synthesis.get_chat_model")
    def test_create_fallback_synthesis_model_returns_runnable(self, mock_get_chat_model: MagicMock):
        """Test that fallback model returns a runnable with structured output."""
        mock_model = MagicMock()
        mock_structured_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured_model
        mock_get_chat_model.return_value = mock_model

        result = create_fallback_synthesis_model()

        assert result == mock_structured_model


class TestCreateSynthesisAgentWithFallback:
    """Test synthesis agent with fallback chain creation (Issue #299-304)."""

    @patch("app.workflows.tasks.aggregation.synthesis.create_synthesis_agent")
    @patch("app.workflows.tasks.aggregation.synthesis.create_fallback_synthesis_model")
    def test_create_synthesis_agent_with_fallback_attaches_fallback(
        self,
        mock_create_fallback: MagicMock,
        mock_create_primary: MagicMock,
    ):
        """Test that fallback chain is properly attached to primary agent."""
        mock_primary_agent = MagicMock()
        mock_fallback_model = MagicMock()
        mock_agent_with_fallback = MagicMock()

        mock_create_primary.return_value = mock_primary_agent
        mock_create_fallback.return_value = mock_fallback_model
        mock_primary_agent.with_fallbacks.return_value = mock_agent_with_fallback

        result = create_synthesis_agent_with_fallback()

        # Verify primary agent was created
        mock_create_primary.assert_called_once()

        # Verify fallback model was created
        mock_create_fallback.assert_called_once()

        # Verify with_fallbacks was called with correct arguments
        mock_primary_agent.with_fallbacks.assert_called_once()
        call_kwargs = mock_primary_agent.with_fallbacks.call_args.kwargs
        assert "fallbacks" in call_kwargs
        assert mock_fallback_model in call_kwargs["fallbacks"]
        assert "exceptions_to_handle" in call_kwargs
        # Should handle Exception, TimeoutError, and GeneratorExit
        exceptions = call_kwargs["exceptions_to_handle"]
        assert Exception in exceptions
        assert TimeoutError in exceptions
        assert GeneratorExit in exceptions

        # Verify result is the agent with fallback
        assert result == mock_agent_with_fallback

    @patch("app.workflows.tasks.aggregation.synthesis.create_synthesis_agent")
    @patch("app.workflows.tasks.aggregation.synthesis.create_fallback_synthesis_model")
    def test_create_synthesis_agent_with_fallback_logs_models(
        self,
        mock_create_fallback: MagicMock,
        mock_create_primary: MagicMock,
    ):
        """Test that agent creation logs primary and fallback models."""
        mock_primary_agent = MagicMock()
        mock_primary_agent.with_fallbacks.return_value = MagicMock()
        mock_create_primary.return_value = mock_primary_agent
        mock_create_fallback.return_value = MagicMock()

        # This test mainly verifies no exceptions are raised during creation
        result = create_synthesis_agent_with_fallback()

        assert result is not None


class TestSynthesizeWithLLM:
    """Test LLM synthesis function."""

    @pytest.mark.asyncio
    @patch("app.workflows.tasks.aggregation_fallback.synthesize_with_fallback_chain", new_callable=AsyncMock)
    async def test_synthesize_with_llm_success(
        self,
        mock_synthesize_with_fallback_chain: AsyncMock,
        sample_analysis_id: AnalysisID,
        sample_validated_findings: list[dict[str, object]],
        sample_conflicts: list[dict[str, str]],
        sample_confidence_scores: dict[str, float],
        sample_llm_response: dict[str, object],
    ):
        """Test successful LLM synthesis flow with tiered fallback chain (Issue #299-304)."""
        # Import FallbackTier enum
        from app.workflows.tasks.aggregation_fallback import FallbackTier

        # Setup mock to return result and tier
        mock_synthesize_with_fallback_chain.return_value = (sample_llm_response, FallbackTier.FULL)

        # Execute the actual synthesize_with_llm function
        result = await synthesize_with_llm(
            validated_findings=sample_validated_findings,
            conflicts=sample_conflicts,
            confidence_scores=sample_confidence_scores,
            analysis_id=sample_analysis_id,
        )

        # Verify synthesize_with_fallback_chain was called with correct args
        mock_synthesize_with_fallback_chain.assert_called_once()
        call_kwargs = mock_synthesize_with_fallback_chain.call_args.kwargs
        assert call_kwargs["validated_findings"] == sample_validated_findings
        assert call_kwargs["conflicts"] == sample_conflicts
        assert call_kwargs["confidence_scores"] == sample_confidence_scores
        assert call_kwargs["analysis_id"] == sample_analysis_id
        assert "full_schema" in call_kwargs

        # Verify result matches expected response
        assert result == sample_llm_response

    @pytest.mark.asyncio
    @patch("app.workflows.tasks.aggregation_fallback.synthesize_with_fallback_chain", new_callable=AsyncMock)
    async def test_synthesize_with_llm_fallback_to_static(
        self,
        mock_synthesize_with_fallback_chain: AsyncMock,
        sample_analysis_id: AnalysisID,
        sample_validated_findings: list[dict[str, object]],
        sample_conflicts: list[dict[str, str]],
        sample_confidence_scores: dict[str, float],
    ):
        """Test synthesize_with_llm falls back to static tier when all LLM tiers fail (Issue #299-304)."""
        # Import FallbackTier enum
        from app.workflows.tasks.aggregation_fallback import FallbackTier

        # Setup mock to return static fallback result
        static_result = {
            "executive_summary": "Analysis completed with 2 specialized agents. Full synthesis unavailable.",
            "key_findings": ["Analysis findings available in agent reports"],
            "synthesis": {
                "technical_analysis": "See individual agent findings for technical details.",
                "implementation_guidance": "Review agent findings for implementation guidance.",
                "risk_assessment": "Risk assessment requires manual review of agent findings.",
                "recommendations": "Recommendations available in agent findings.",
            },
            "coverage_score": 0.3,
            "generation_notes": "Static fallback - full synthesis unavailable.",
        }
        mock_synthesize_with_fallback_chain.return_value = (static_result, FallbackTier.STATIC)

        # Execute
        result = await synthesize_with_llm(
            validated_findings=sample_validated_findings,
            conflicts=sample_conflicts,
            confidence_scores=sample_confidence_scores,
            analysis_id=sample_analysis_id,
        )

        # Verify result is the static fallback
        assert result == static_result
        assert "generation_notes" in result
        assert "static fallback" in result["generation_notes"].lower()

    @pytest.mark.asyncio
    @patch("app.workflows.tasks.aggregation_fallback.synthesize_with_fallback_chain", new_callable=AsyncMock)
    async def test_synthesize_with_llm_fallback_to_minimal_schema(
        self,
        mock_synthesize_with_fallback_chain: AsyncMock,
        sample_analysis_id: AnalysisID,
        sample_validated_findings: list[dict[str, object]],
        sample_conflicts: list[dict[str, str]],
        sample_confidence_scores: dict[str, float],
    ):
        """Test synthesize_with_llm can use minimal schema tier (Issue #299-304)."""
        # Import FallbackTier enum
        from app.workflows.tasks.aggregation_fallback import FallbackTier

        # Setup mock to return minimal schema result
        minimal_result = {
            "executive_summary": "Quick summary from minimal schema tier.",
            "key_findings": [
                "Finding 1",
                "Finding 2",
                "Finding 3",
            ],
            "synthesis": {
                "technical_analysis": "Brief analysis",
                "implementation_guidance": "Basic steps",
                "risk_assessment": "Key risks",
                "recommendations": "Top recommendations",
            },
            "coverage_score": 0.5,
            "generation_notes": "Degraded mode - partial content generated",
        }
        mock_synthesize_with_fallback_chain.return_value = (minimal_result, FallbackTier.MINIMAL)

        # Execute
        result = await synthesize_with_llm(
            validated_findings=sample_validated_findings,
            conflicts=sample_conflicts,
            confidence_scores=sample_confidence_scores,
            analysis_id=sample_analysis_id,
        )

        # Verify result uses minimal schema
        assert result == minimal_result
        assert "generation_notes" in result

    @pytest.mark.asyncio
    @patch("app.workflows.tasks.aggregation_fallback.synthesize_with_fallback_chain", new_callable=AsyncMock)
    async def test_synthesize_with_llm_empty_findings(
        self,
        mock_synthesize_with_fallback_chain: AsyncMock,
        sample_analysis_id: AnalysisID,
        sample_llm_response: dict[str, object],
    ):
        """Test synthesize_with_llm with empty findings."""
        # Import FallbackTier enum
        from app.workflows.tasks.aggregation_fallback import FallbackTier

        # Setup mock
        mock_synthesize_with_fallback_chain.return_value = (sample_llm_response, FallbackTier.FULL)

        # Execute with empty findings
        result = await synthesize_with_llm(
            validated_findings=[],
            conflicts=[],
            confidence_scores={},
            analysis_id=sample_analysis_id,
        )

        # Verify synthesize_with_fallback_chain was called
        mock_synthesize_with_fallback_chain.assert_called_once()

        # Verify result is returned
        assert result == sample_llm_response

    @pytest.mark.asyncio
    @patch("app.workflows.tasks.aggregation_fallback.synthesize_with_fallback_chain", new_callable=AsyncMock)
    async def test_synthesize_with_llm_many_conflicts(
        self,
        mock_synthesize_with_fallback_chain: AsyncMock,
        sample_analysis_id: AnalysisID,
        sample_validated_findings: list[dict[str, object]],
        sample_confidence_scores: dict[str, float],
        sample_llm_response: dict[str, object],
    ):
        """Test synthesize_with_llm with multiple conflicts."""
        # Import FallbackTier enum
        from app.workflows.tasks.aggregation_fallback import FallbackTier

        # Setup many conflicts
        conflicts = [
            {"agent_1": "tech_comparator", "agent_2": "security_auditor", "conflict": "Conflict 1"},
            {
                "agent_1": "implementation_planner",
                "agent_2": "performance_analyst",
                "conflict": "Conflict 2",
            },
            {
                "agent_1": "dependency_mapper",
                "agent_2": "trend_validator",
                "conflict": "Conflict 3",
            },
        ]

        # Setup mock
        mock_synthesize_with_fallback_chain.return_value = (sample_llm_response, FallbackTier.FULL)

        # Execute
        result = await synthesize_with_llm(
            validated_findings=sample_validated_findings,
            conflicts=conflicts,
            confidence_scores=sample_confidence_scores,
            analysis_id=sample_analysis_id,
        )

        # Verify conflicts were passed to synthesize_with_fallback_chain
        call_kwargs = mock_synthesize_with_fallback_chain.call_args.kwargs
        assert len(call_kwargs["conflicts"]) == 3  # 3 conflicts

        # Verify result is returned
        assert result == sample_llm_response

    @pytest.mark.asyncio
    @patch("app.workflows.tasks.aggregation_fallback.synthesize_with_fallback_chain", new_callable=AsyncMock)
    async def test_synthesize_with_llm_reduced_tier_success(
        self,
        mock_synthesize_with_fallback_chain: AsyncMock,
        sample_analysis_id: AnalysisID,
        sample_validated_findings: list[dict[str, object]],
        sample_conflicts: list[dict[str, str]],
        sample_confidence_scores: dict[str, float],
        sample_llm_response: dict[str, object],
    ):
        """Test synthesize_with_llm succeeds with REDUCED tier (faster model)."""
        # Import FallbackTier enum
        from app.workflows.tasks.aggregation_fallback import FallbackTier

        # Setup mock to return reduced tier result
        mock_synthesize_with_fallback_chain.return_value = (sample_llm_response, FallbackTier.REDUCED)

        # Execute
        result = await synthesize_with_llm(
            validated_findings=sample_validated_findings,
            conflicts=sample_conflicts,
            confidence_scores=sample_confidence_scores,
            analysis_id=sample_analysis_id,
        )

        # Verify result is returned
        assert result == sample_llm_response
