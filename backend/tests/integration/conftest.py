"""Integration test configuration and fixtures.

Integration tests use REAL database connections and REAL API keys.
They send traces to Langfuse for observability.

IMPORTANT: Integration tests require:
- Running PostgreSQL with pgvector (port 5437)
- Valid API keys in backend/.env (OPENAI_API_KEY or GOOGLE_API_KEY)
- Langfuse credentials (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY)
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

# Enable Langfuse tracing for integration tests
# Integration tests should send traces to Langfuse for real workflow observability
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# Set project for integration tests
# This helps organize integration test traces separately from production traces
os.environ.setdefault("LANGCHAIN_PROJECT", "skillforge-integration-tests")

# Note: Langfuse credentials should be set via:
# 1. .env file (loaded above)
# 2. Environment variables (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST)
# If not set, Langfuse will be disabled but tests will still run
#
# DEBUG: Check if Langfuse is configured for tracing
if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
    print(f"✓ Langfuse configured (host: {os.getenv('LANGFUSE_HOST', 'default')})")
else:
    print("✗ Langfuse credentials not set - traces will not be sent")
    print("  Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env to enable tracing")
