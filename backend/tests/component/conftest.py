"""Component test configuration and fixtures.

Component tests verify business logic with MOCKED external dependencies.
They test the integration of multiple internal modules without hitting:
- Real databases (PostgreSQL)
- Real external APIs (OpenAI, LangSmith)
- Real network calls

This differs from:
- Unit tests (tests/unit/): Test single functions in isolation
- Integration tests (tests/integration/): Test with REAL databases and APIs
- Smoke tests (tests/smoke/): End-to-end tests with real external services

Component tests use placeholder API keys and mock database operations.
"""

# Component tests use the default placeholder API keys from root conftest.py
# No special configuration needed - they inherit mocked behavior
