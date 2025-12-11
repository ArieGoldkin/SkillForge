"""Integration test configuration and fixtures.

Integration tests use REAL database connections and REAL API keys.
They send traces to LangSmith for observability.

IMPORTANT: Integration tests require:
- Running PostgreSQL with pgvector (port 5437)
- Valid API keys in backend/.env (OPENAI_API_KEY or GOOGLE_API_KEY)
"""

import os
from pathlib import Path

# CRITICAL: Load .env BEFORE any other imports to get real API keys
# Integration tests need real keys, not placeholders
_env_file = Path(__file__).parent.parent.parent / ".env"
if _env_file.exists():
    from dotenv import load_dotenv

    # Override=True ensures we get real keys from .env, not placeholders
    load_dotenv(_env_file, override=True)

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
#
# DEBUG: Check if API key is available for tracing
if os.getenv("LANGSMITH_API_KEY"):
    print(f"✓ LANGSMITH_API_KEY is set (length: {len(os.getenv('LANGSMITH_API_KEY'))})")
else:
    print("✗ LANGSMITH_API_KEY not set - traces will not be sent to LangSmith")
    print("  Set LANGSMITH_API_KEY in .env or environment to enable tracing")
