"""Integration test configuration and fixtures.

Integration tests should send traces to LangSmith for observability.
This conftest enables LangSmith tracing for all integration tests.
"""

import os

# Enable LangSmith tracing for integration tests
# Integration tests should send traces to LangSmith for real workflow observability
# The API key should be available via MCP or .env file
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGSMITH_TRACING"] = "true"

# Set LangSmith project for integration tests
# This helps organize integration test traces separately from production traces
os.environ.setdefault("LANGCHAIN_PROJECT", "skillforge-integration-tests")

# Note: LANGSMITH_API_KEY should be set via:
# 1. .env file (loaded by main conftest.py)
# 2. MCP server configuration
# 3. Environment variables
# If not set, LangSmith will log warnings but tests will still run
