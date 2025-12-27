"""Unit tests for Issue #539 - State validation guards.

Tests defensive state access in graph_builder.py, evaluator.py, and state_accessors.py
to ensure graceful handling of missing state fields instead of raising KeyErrors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.domains.analysis.workflows.evaluation.evaluator import evaluate_agent_quality
from app.domains.analysis.workflows.graph_builder import (
    _chunk_and_embed_node,
    _generate_embedding_node,
    _supervisor_node,
)
from app.domains.analysis.workflows.state_accessors import get_analysis_id

if TYPE_CHECKING:
    from app.domains.analysis.workflows.state import AnalysisState

# Test UUID for analysis_id
TEST_ANALYSIS_ID = str(uuid4())


class TestGenerateEmbeddingNode:
    """Test _generate_embedding_node with missing state fields."""

    @pytest.mark.asyncio
    async def test_missing_raw_content_returns_empty_dict(self) -> None:
        """Test that missing raw_content returns empty dict gracefully."""
        state: AnalysisState = {
            "analysis_id": TEST_ANALYSIS_ID,
            "url": "https://example.com",
            # Missing raw_content
        }

        result = await _generate_embedding_node(state)

        # Should return empty dict instead of raising KeyError
        assert result == {}

    @pytest.mark.asyncio
    async def test_missing_analysis_id_returns_empty_dict(self) -> None:
        """Test that missing analysis_id returns empty dict gracefully."""
        state: AnalysisState = {
            "url": "https://example.com",
            "raw_content": "Test content",
            # Missing analysis_id
        }

        result = await _generate_embedding_node(state)

        # Should return empty dict instead of raising KeyError
        assert result == {}

    @pytest.mark.asyncio
    async def test_both_missing_returns_empty_dict(self) -> None:
        """Test that missing both raw_content and analysis_id returns empty dict."""
        state: AnalysisState = {
            "url": "https://example.com",
            # Missing both raw_content and analysis_id
        }

        result = await _generate_embedding_node(state)

        # Should return empty dict instead of raising KeyError
        assert result == {}

    @pytest.mark.asyncio
    async def test_abort_signal_returns_empty_dict(self) -> None:
        """Test that should_abort flag returns empty dict without processing."""
        state: AnalysisState = {
            "analysis_id": TEST_ANALYSIS_ID,
            "url": "https://example.com",
            "raw_content": "Test content",
            "should_abort": True,
            "abort_reason": "Extraction failed",
        }

        result = await _generate_embedding_node(state)

        # Should return empty dict when aborting
        assert result == {}

    @pytest.mark.asyncio
    async def test_empty_raw_content_returns_empty_dict(self) -> None:
        """Test that empty string raw_content returns empty dict."""
        state: AnalysisState = {
            "analysis_id": TEST_ANALYSIS_ID,
            "url": "https://example.com",
            "raw_content": "",  # Empty string
        }

        result = await _generate_embedding_node(state)

        # Should return empty dict for empty content
        assert result == {}


class TestChunkAndEmbedNode:
    """Test _chunk_and_embed_node with missing state fields."""

    @pytest.mark.asyncio
    async def test_missing_raw_content_returns_zero_counts(self) -> None:
        """Test that missing raw_content returns zero counts gracefully."""
        state: AnalysisState = {
            "analysis_id": TEST_ANALYSIS_ID,
            "url": "https://example.com",
            # Missing raw_content
        }

        with patch("app.core.config.settings.ENABLE_COARSE_TO_FINE", new=True):
            result = await _chunk_and_embed_node(state)

        # Should return zero counts instead of raising KeyError
        assert result == {
            "chunk_counts": {"coarse": 0, "fine": 0, "summaries": 0},
            "dedup_stats": {"kept": 0, "dropped": 0},
        }

    @pytest.mark.asyncio
    async def test_missing_analysis_id_returns_zero_counts(self) -> None:
        """Test that missing analysis_id returns zero counts gracefully."""
        state: AnalysisState = {
            "url": "https://example.com",
            "raw_content": "Test content",
            # Missing analysis_id
        }

        with patch("app.core.config.settings.ENABLE_COARSE_TO_FINE", new=True):
            result = await _chunk_and_embed_node(state)

        # Should return zero counts instead of raising KeyError
        assert result == {
            "chunk_counts": {"coarse": 0, "fine": 0, "summaries": 0},
            "dedup_stats": {"kept": 0, "dropped": 0},
        }

    @pytest.mark.asyncio
    async def test_both_missing_returns_zero_counts(self) -> None:
        """Test that missing both raw_content and analysis_id returns zero counts."""
        state: AnalysisState = {
            "url": "https://example.com",
            # Missing both raw_content and analysis_id
        }

        with patch("app.core.config.settings.ENABLE_COARSE_TO_FINE", new=True):
            result = await _chunk_and_embed_node(state)

        # Should return zero counts instead of raising KeyError
        assert result == {
            "chunk_counts": {"coarse": 0, "fine": 0, "summaries": 0},
            "dedup_stats": {"kept": 0, "dropped": 0},
        }

    @pytest.mark.asyncio
    async def test_abort_signal_returns_empty_dict(self) -> None:
        """Test that should_abort flag returns empty dict without processing."""
        state: AnalysisState = {
            "analysis_id": TEST_ANALYSIS_ID,
            "url": "https://example.com",
            "raw_content": "Test content",
            "should_abort": True,
            "abort_reason": "Extraction failed",
        }

        result = await _chunk_and_embed_node(state)

        # Should return empty dict when aborting
        assert result == {}

    @pytest.mark.asyncio
    async def test_feature_flag_disabled_returns_zero_counts(self) -> None:
        """Test that disabled ENABLE_COARSE_TO_FINE returns zero counts."""
        state: AnalysisState = {
            "analysis_id": TEST_ANALYSIS_ID,
            "url": "https://example.com",
            "raw_content": "Test content",
        }

        with patch("app.core.config.settings.ENABLE_COARSE_TO_FINE", new=False):
            result = await _chunk_and_embed_node(state)

        # Should return zero counts when feature is disabled
        assert result == {
            "chunk_counts": {"coarse": 0, "fine": 0, "summaries": 0},
            "dedup_stats": {"kept": 0, "dropped": 0},
        }


class TestSupervisorNode:
    """Test _supervisor_node with missing state fields."""

    @pytest.mark.asyncio
    async def test_missing_raw_content_returns_empty_dict(self) -> None:
        """Test that missing raw_content returns empty dict gracefully."""
        state: AnalysisState = {
            "analysis_id": TEST_ANALYSIS_ID,
            "url": "https://example.com",
            # Missing raw_content
        }

        result = await _supervisor_node(state)

        # Should return empty dict instead of raising KeyError
        assert result == {}

    @pytest.mark.asyncio
    async def test_missing_analysis_id_returns_empty_dict(self) -> None:
        """Test that missing analysis_id returns empty dict gracefully."""
        state: AnalysisState = {
            "url": "https://example.com",
            "raw_content": "Test content",
            # Missing analysis_id
        }

        result = await _supervisor_node(state)

        # Should return empty dict instead of raising KeyError
        assert result == {}

    @pytest.mark.asyncio
    async def test_missing_content_type_uses_default_article(self) -> None:
        """Test that missing content_type defaults to 'article'."""
        state: AnalysisState = {
            "analysis_id": TEST_ANALYSIS_ID,
            "url": "https://example.com",
            "raw_content": "Test content",
            # Missing content_type
        }

        mock_supervisor_result = {
            "supervisor_decision": {
                "agents": ["actionable"],
                "priority": ["actionable"],
                "reasoning": "Test reasoning",
                "confidence": 0.8,
            }
        }

        with patch(
            "app.domains.analysis.workflows.graph_builder.supervisor_route",
            new_callable=AsyncMock,
            return_value=mock_supervisor_result,
        ) as mock_supervisor:
            result = await _supervisor_node(state)

            # Verify supervisor_route was called with default "article"
            mock_supervisor.assert_called_once()
            call_args = mock_supervisor.call_args
            assert call_args[0][1] == "article"  # content_type argument

            # Should return supervisor decision
            assert result == mock_supervisor_result

    @pytest.mark.asyncio
    async def test_both_missing_returns_empty_dict(self) -> None:
        """Test that missing both raw_content and analysis_id returns empty dict."""
        state: AnalysisState = {
            "url": "https://example.com",
            # Missing both raw_content and analysis_id
        }

        result = await _supervisor_node(state)

        # Should return empty dict instead of raising KeyError
        assert result == {}

    @pytest.mark.asyncio
    async def test_abort_signal_returns_empty_dict(self) -> None:
        """Test that should_abort flag returns empty dict without processing."""
        state: AnalysisState = {
            "analysis_id": TEST_ANALYSIS_ID,
            "url": "https://example.com",
            "raw_content": "Test content",
            "should_abort": True,
            "abort_reason": "Extraction failed",
        }

        result = await _supervisor_node(state)

        # Should return empty dict when aborting
        assert result == {}


class TestEvaluateAgentQuality:
    """Test evaluate_agent_quality with missing state fields."""

    @pytest.mark.asyncio
    async def test_missing_analysis_id_returns_empty_results(self) -> None:
        """Test that missing analysis_id returns empty evaluation_results."""
        state: AnalysisState = {
            "url": "https://example.com",
            # Missing analysis_id
            "agent_findings": [
                {
                    "agent_type": "actionable",
                    "findings": {"key": "value"},
                    "confidence_score": 0.8,
                }
            ],
        }

        result = await evaluate_agent_quality(state)

        # Should set empty evaluation_results and return state
        assert result.get("evaluation_results") == {}
        # Other state fields should be preserved
        assert result.get("url") == "https://example.com"

    @pytest.mark.asyncio
    async def test_empty_agent_findings_returns_empty_results(self) -> None:
        """Test that empty agent_findings returns empty evaluation_results."""
        state: AnalysisState = {
            "analysis_id": TEST_ANALYSIS_ID,
            "url": "https://example.com",
            "agent_findings": [],  # Empty findings
        }

        result = await evaluate_agent_quality(state)

        # Should set empty evaluation_results
        assert result.get("evaluation_results") == {}

    @pytest.mark.asyncio
    async def test_missing_agent_findings_returns_empty_results(self) -> None:
        """Test that missing agent_findings returns empty evaluation_results."""
        state: AnalysisState = {
            "analysis_id": TEST_ANALYSIS_ID,
            "url": "https://example.com",
            # Missing agent_findings
        }

        result = await evaluate_agent_quality(state)

        # Should set empty evaluation_results
        assert result.get("evaluation_results") == {}

    @pytest.mark.asyncio
    async def test_valid_state_emits_events(self) -> None:
        """Test that valid state emits SSE events correctly."""
        state: AnalysisState = {
            "analysis_id": TEST_ANALYSIS_ID,
            "url": "https://example.com",
            "agent_findings": [
                {
                    "agent_type": "actionable",
                    "findings": {"takeaways": ["Test takeaway"]},
                    "confidence_score": 0.9,
                }
            ],
        }

        with patch(
            "app.domains.analysis.workflows.evaluation.evaluator.emit_streaming_event",
            new_callable=AsyncMock,
        ) as mock_emit:
            result = await evaluate_agent_quality(state)

            # Verify SSE event was emitted
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args
            assert call_args[0][0] == "evaluation"
            assert call_args[1]["analysis_id"] == TEST_ANALYSIS_ID
            assert call_args[1]["stage"] == "actionable"
            assert call_args[1]["status"] == "complete"

            # Verify evaluation_results were set
            assert "actionable" in result.get("evaluation_results", {})


class TestGetAnalysisId:
    """Test get_analysis_id accessor function."""

    def test_missing_analysis_id_returns_none(self) -> None:
        """Test that missing analysis_id returns None."""
        state: AnalysisState = {
            "url": "https://example.com",
            # Missing analysis_id
        }

        result = get_analysis_id(state)

        # Should return None instead of raising KeyError
        assert result is None

    def test_present_analysis_id_returns_value(self) -> None:
        """Test that present analysis_id returns the value."""
        state: AnalysisState = {
            "analysis_id": TEST_ANALYSIS_ID,
            "url": "https://example.com",
        }

        result = get_analysis_id(state)

        # Should return the analysis_id value
        assert result == TEST_ANALYSIS_ID


class TestCombinedMissingFields:
    """Test scenarios with multiple missing fields for comprehensive coverage."""

    @pytest.mark.asyncio
    async def test_generate_embedding_handles_combined_missing_gracefully(self) -> None:
        """Test that _generate_embedding_node handles multiple missing fields gracefully."""
        state: AnalysisState = {
            "url": "https://example.com",
            # Missing raw_content and analysis_id
        }

        # Should not raise, just return empty dict
        result = await _generate_embedding_node(state)
        assert result == {}

    @pytest.mark.asyncio
    async def test_chunk_and_embed_handles_combined_missing_gracefully(self) -> None:
        """Test that _chunk_and_embed_node handles multiple missing fields gracefully."""
        state: AnalysisState = {
            "url": "https://example.com",
            # Missing raw_content and analysis_id
        }

        with patch("app.core.config.settings.ENABLE_COARSE_TO_FINE", new=True):
            # Should not raise, just return zero counts
            result = await _chunk_and_embed_node(state)

        assert result == {
            "chunk_counts": {"coarse": 0, "fine": 0, "summaries": 0},
            "dedup_stats": {"kept": 0, "dropped": 0},
        }

    @pytest.mark.asyncio
    async def test_supervisor_handles_combined_missing_gracefully(self) -> None:
        """Test that _supervisor_node handles multiple missing fields gracefully."""
        state: AnalysisState = {
            "url": "https://example.com",
            # Missing raw_content and analysis_id
        }

        # Should not raise, just return empty dict
        result = await _supervisor_node(state)
        assert result == {}

    @pytest.mark.asyncio
    async def test_evaluator_handles_missing_analysis_id_gracefully(self) -> None:
        """Test that evaluate_agent_quality handles missing analysis_id gracefully."""
        state: AnalysisState = {
            "url": "https://example.com",
            # Missing analysis_id
            "agent_findings": [{"agent_type": "actionable", "findings": {}}],
        }

        # Should not raise, just set empty evaluation_results
        result = await evaluate_agent_quality(state)
        assert result.get("evaluation_results") == {}

    @pytest.mark.asyncio
    async def test_all_nodes_handle_empty_state_gracefully(self) -> None:
        """Integration test: all nodes handle nearly empty state without crashing."""
        minimal_state: AnalysisState = {
            "url": "https://example.com",
            # No other fields
        }

        # All nodes should handle gracefully
        result1 = await _generate_embedding_node(minimal_state)
        assert result1 == {}

        with patch("app.core.config.settings.ENABLE_COARSE_TO_FINE", new=True):
            result2 = await _chunk_and_embed_node(minimal_state)
        assert "chunk_counts" in result2

        result3 = await _supervisor_node(minimal_state)
        assert result3 == {}

        result4 = await evaluate_agent_quality(minimal_state)
        assert result4.get("evaluation_results") == {}
