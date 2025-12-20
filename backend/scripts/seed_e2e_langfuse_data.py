#!/usr/bin/env python
"""Seed E2E test data with Langfuse trace integration.

This script creates a completed analysis with artifact and Langfuse trace
for E2E testing of the Langfuse integration. The script:

1. Creates a Langfuse trace programmatically with known ID
2. Creates a matching Analysis record (status: completed)
3. Creates an Artifact with trace_id linking to Langfuse
4. Outputs IDs for CI environment variables

Usage:
    # Normal mode (creates data)
    poetry run python scripts/seed_e2e_langfuse_data.py

    # Output format for CI:
    E2E_ARTIFACT_ID={uuid}
    E2E_ANALYSIS_ID={uuid}
    E2E_TRACE_ID={uuid}

Environment:
    DATABASE_URL - PostgreSQL connection string
    LANGFUSE_PUBLIC_KEY - Langfuse public key
    LANGFUSE_SECRET_KEY - Langfuse secret key
    LANGFUSE_HOST - Langfuse host (default: http://localhost:3000)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.langfuse_service import get_langfuse_service
from app.core.logging import get_logger

# Load environment variables BEFORE app config initialization
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

logger = get_logger(__name__)

# E2E Test Constants
SEED_URL = "https://e2e-test.skillforge.dev/langfuse-integration"
SEED_TITLE = "E2E Langfuse Integration Test"
SEED_CONTENT_TYPE = "article"

SEED_MARKDOWN = """# E2E Langfuse Integration Test Artifact

This artifact was created for E2E testing of Langfuse trace integration.

## Key Features

- **Trace Linking**: This artifact links to a Langfuse trace via `trace_id`
- **Metadata**: Includes topics, complexity, and other metadata
- **E2E Testing**: Used to verify artifact-trace integration in CI

## Technical Details

The artifact creation process:

1. **Langfuse Trace**: Created programmatically with SDK
2. **Analysis Record**: Status set to 'completed'
3. **Artifact Creation**: Links to trace via `trace_id` field

```python
def verify_langfuse_integration():
    '''Verify artifact has trace_id linking to Langfuse.'''
    artifact = fetch_artifact(artifact_id)
    assert artifact.trace_id is not None
    trace = langfuse.get_trace(artifact.trace_id)
    assert trace is not None
    return True
```

## Testing Scenarios

This data enables E2E tests for:

- Artifact page displays trace link
- Trace link navigates to Langfuse UI
- Trace metadata matches artifact metadata
- Observability dashboard shows trace data

## Metadata

- **Topics**: Langfuse, Observability, Testing, E2E
- **Complexity**: Medium
- **Test Type**: Integration Test
"""

SEED_METADATA = {
    "topics": ["Langfuse", "Observability", "Testing", "E2E", "Integration"],
    "complexity": "medium",
    "test_type": "integration",
    "created_by": "seed_e2e_langfuse_data.py",
}


async def create_langfuse_trace(trace_id: str) -> bool:
    """Create a Langfuse trace programmatically using low-level API.

    Args:
        trace_id: Known trace ID for E2E testing

    Returns:
        True if trace created successfully, False otherwise

    Note:
        This is optional - E2E tests will work even if Langfuse is unavailable.
        The trace_id is stored in the database regardless.

    """
    service = get_langfuse_service()
    if not service or not service.sdk_client:
        logger.warning(
            "langfuse_unavailable",
            message="Langfuse client not available - trace creation skipped",
        )
        return False

    try:
        # Use low-level trace API (Langfuse v3 pattern)
        # The Langfuse Python SDK doesn't have a direct .trace() method
        # Instead, use the @observe decorator pattern or REST API
        # For E2E testing, we'll use the REST API directly

        import httpx

        langfuse_host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")

        if not public_key or not secret_key:
            logger.warning("langfuse_credentials_missing")
            return False

        # Create trace via REST API using the ingestion endpoint
        # Langfuse REST API: https://langfuse.com/docs/integrations/api
        # Note: /api/public/traces is GET-only; use /api/public/ingestion for writes
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{langfuse_host}/api/public/ingestion",
                json={
                    "batch": [
                        {
                            "type": "trace-create",
                            "id": trace_id,  # Event ID
                            "timestamp": datetime.now(UTC).isoformat(),
                            "body": {
                                "id": trace_id,
                                "name": "E2E Test Analysis - Langfuse Integration",
                                "metadata": {
                                    "test_type": "e2e",
                                    "source": "seed_e2e_langfuse_data.py",
                                    "url": SEED_URL,
                                    "topics": SEED_METADATA["topics"],
                                },
                                "tags": ["e2e", "test", "langfuse-integration"],
                            },
                        }
                    ]
                },
                auth=(public_key, secret_key),
                timeout=10.0,
            )

            # 207 Multi-Status is success for batch operations
            if response.status_code in {200, 201, 207}:
                # Check if the batch had errors
                result = response.json()
                if result.get("errors") and len(result["errors"]) > 0:
                    logger.warning(
                        "langfuse_trace_creation_partial_failure",
                        status_code=response.status_code,
                        errors=result["errors"],
                    )
                    return False
                logger.info(
                    "langfuse_trace_created",
                    trace_id=trace_id,
                    status_code=response.status_code,
                    message="Langfuse trace created via REST API",
                )
                return True
            else:
                logger.warning(
                    "langfuse_trace_creation_failed",
                    status_code=response.status_code,
                    response=response.text[:200],
                )
                return False

    except Exception as e:
        logger.error(
            "langfuse_trace_creation_failed",
            error=str(e),
            trace_id=trace_id,
            exc_info=True,
        )
        return False


async def seed_database(
    database_url: str,
    analysis_id: uuid.UUID,
    artifact_id: uuid.UUID,
    trace_id: str,
) -> bool:
    """Seed the database with analysis and artifact records.

    Args:
        database_url: PostgreSQL connection string
        analysis_id: UUID for analysis record
        artifact_id: UUID for artifact record
        trace_id: Langfuse trace ID to link

    Returns:
        True if seeding successful, False otherwise

    """
    try:
        engine = create_async_engine(database_url)

        async with engine.begin() as conn:
            # Create Analysis record
            await conn.execute(
                text("""
                    INSERT INTO analyses (
                        id, url, content_type, title, status,
                        created_at, updated_at
                    )
                    VALUES (
                        :id, :url, :content_type, :title, 'completed',
                        NOW(), NOW()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        updated_at = NOW(),
                        status = 'completed'
                """),
                {
                    "id": str(analysis_id),
                    "url": SEED_URL,
                    "content_type": SEED_CONTENT_TYPE,
                    "title": SEED_TITLE,
                },
            )

            # Create Artifact record with trace_id
            await conn.execute(
                text("""
                    INSERT INTO artifacts (
                        id, analysis_id, markdown_content, version,
                        artifact_metadata, download_count, trace_id,
                        created_at
                    )
                    VALUES (
                        :id, :analysis_id, :markdown_content, 1,
                        CAST(:artifact_metadata AS jsonb), 0, :trace_id,
                        NOW()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        trace_id = EXCLUDED.trace_id,
                        artifact_metadata = EXCLUDED.artifact_metadata
                """),
                {
                    "id": str(artifact_id),
                    "analysis_id": str(analysis_id),
                    "markdown_content": SEED_MARKDOWN,
                    "artifact_metadata": json.dumps(SEED_METADATA),
                    "trace_id": trace_id,
                },
            )

        await engine.dispose()

        logger.info(
            "database_seeded",
            analysis_id=str(analysis_id),
            artifact_id=str(artifact_id),
            trace_id=trace_id,
        )

        return True

    except Exception as e:
        logger.error(
            "database_seeding_failed",
            error=str(e),
            exc_info=True,
        )
        return False


async def main() -> None:
    """Main entry point for seeding script."""
    # Check for required environment variables
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    # Convert to async URL
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Generate deterministic IDs for E2E testing
    # Using fixed UUIDs for reproducibility in CI
    analysis_id = uuid.UUID("e2e00000-0000-0000-0000-000000000001")
    artifact_id = uuid.UUID("e2e00000-0000-0000-0000-000000000002")
    trace_id = "e2e-trace-langfuse-integration-test"

    print("=" * 60)
    print("E2E Langfuse Data Seeding")
    print("=" * 60)
    print(f"Analysis ID: {analysis_id}")
    print(f"Artifact ID: {artifact_id}")
    print(f"Trace ID: {trace_id}")
    print("")

    # Step 1: Create Langfuse trace
    print("Step 1: Creating Langfuse trace...")
    trace_created = await create_langfuse_trace(trace_id)
    if trace_created:
        print("  ✓ Langfuse trace created")
    else:
        print("  ⚠ Langfuse trace creation skipped (client unavailable)")
        print("    E2E tests requiring Langfuse will be skipped")

    # Step 2: Seed database
    print("\nStep 2: Seeding database...")
    db_seeded = await seed_database(database_url, analysis_id, artifact_id, trace_id)
    if not db_seeded:
        print("  ✗ Database seeding failed")
        sys.exit(1)
    print("  ✓ Database seeded")

    # Step 3: Output IDs for CI
    print("\n" + "=" * 60)
    print("E2E Environment Variables (copy to CI):")
    print("=" * 60)
    print(f"E2E_ARTIFACT_ID={artifact_id}")
    print(f"E2E_ANALYSIS_ID={analysis_id}")
    print(f"E2E_TRACE_ID={trace_id}")
    print("")
    print("Seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())
