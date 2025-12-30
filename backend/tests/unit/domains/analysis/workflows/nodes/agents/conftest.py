"""Shared fixtures for agent node tests.

These fixtures mock external dependencies (Redis, database) that agent nodes
interact with during error handling, preventing infrastructure requirements
in unit tests.
"""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_agent_error_handling():
    """Mock emit_agent_progress and error_recorder to avoid Redis/DB calls.

    Agent nodes call these functions during error handling. Without mocking,
    tests would require Redis to be running, causing timeouts in unit tests.

    Note: error_recorder is imported locally inside handle_agent_node_error,
    so we patch it at its source module location.
    """
    with (
        patch(
            "app.domains.analysis.workflows.agents.base.emit_agent_progress",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.analysis.services.persistence.error_recorder.error_recorder",
        ) as mock_recorder,
    ):
        # Configure error_recorder mock
        mock_recorder.record = AsyncMock()
        yield
