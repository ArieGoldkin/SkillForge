"""Unit tests for LangSmith metrics service."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.services.metrics.langsmith import LangSmithMetricsService


@pytest.fixture
def metrics_service() -> LangSmithMetricsService:
    """Create metrics service instance."""
    return LangSmithMetricsService()


@pytest.mark.asyncio
async def test_get_agent_metrics_success(metrics_service: LangSmithMetricsService) -> None:
    """Test successful metrics retrieval."""
    result = await metrics_service.get_agent_metrics("tech_comparator")

    # Verify result structure
    assert "success_rate" in result
    assert "avg_latency_ms" in result
    assert "total_tokens" in result
    assert "error_rate" in result
    assert "run_count" in result

    # Verify types
    assert isinstance(result["success_rate"], float)
    assert isinstance(result["avg_latency_ms"], float)
    assert isinstance(result["total_tokens"], int)
    assert isinstance(result["error_rate"], float)
    assert isinstance(result["run_count"], int)


@pytest.mark.asyncio
async def test_get_agent_metrics_with_time_range(metrics_service: LangSmithMetricsService) -> None:
    """Test metrics retrieval with time range."""
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    time_range = (start_time, end_time)

    result = await metrics_service.get_agent_metrics("tech_comparator", time_range)

    # Should return metrics structure
    assert "success_rate" in result
    assert "avg_latency_ms" in result


@pytest.mark.asyncio
async def test_get_agent_metrics_no_client() -> None:
    """Test metrics service handles missing LangSmith client gracefully."""
    with patch(
        "app.services.metrics.langsmith.Client",
        side_effect=ConnectionError("Client unavailable"),
    ):
        service = LangSmithMetricsService()
        result = await service.get_agent_metrics("tech_comparator")

        # Should return default/empty metrics
        assert result["success_rate"] == 0.0
        assert result["run_count"] == 0


@pytest.mark.asyncio
async def test_get_workflow_metrics(metrics_service: LangSmithMetricsService) -> None:
    """Test workflow metrics retrieval."""
    analysis_id = "test-analysis-id"
    result = await metrics_service.get_workflow_metrics(analysis_id)

    # Verify result structure (may be empty if client unavailable)
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_get_workflow_metrics_no_client() -> None:
    """Test workflow metrics handles missing client gracefully."""
    with patch(
        "app.services.metrics.langsmith.Client",
        side_effect=ConnectionError("Client unavailable"),
    ):
        service = LangSmithMetricsService()
        result = await service.get_workflow_metrics("test-id")

        # Should return empty dict
        assert result == {}
