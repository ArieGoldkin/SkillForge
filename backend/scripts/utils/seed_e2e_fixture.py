"""Seed a minimal E2E fixture for Playwright tests.

This script creates one completed analysis with an artifact for E2E testing.
Run via: python -m scripts.seed_e2e_fixture
"""

import asyncio
import os
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

SEED_URL = "https://example.com/e2e-seed"
SEED_MD = """# E2E Seed Artifact

This is a deterministic artifact seeded for Playwright E2E tests.

## Code Examples

```python
def example_function():
    return "Hello from E2E seed"
```
"""


async def main() -> None:
    """Seed the database with a test fixture if empty."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not set, skipping seed")
        return

    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        # Check if we already have completed analyses
        res = await conn.execute(text("SELECT COUNT(*) FROM analyses WHERE status='completed'"))
        count = int(res.scalar() or 0)
        if count > 0:
            print(f"Found {count} completed analyses, skipping seed")
            return

        analysis_id = str(uuid.uuid4())
        artifact_id = str(uuid.uuid4())

        await conn.execute(
            text("""
                INSERT INTO analyses (id, url, content_type, title, status, created_at, updated_at)
                VALUES (:id, :url, :content_type, :title, 'completed', NOW(), NOW())
            """),
            {
                "id": analysis_id,
                "url": SEED_URL,
                "content_type": "article",
                "title": "E2E Seed Analysis",
            },
        )

        await conn.execute(
            text("""
                INSERT INTO artifacts (id, analysis_id, markdown_content, version, download_count, created_at)
                VALUES (:id, :analysis_id, :markdown_content, 1, 0, NOW())
            """),
            {
                "id": artifact_id,
                "analysis_id": analysis_id,
                "markdown_content": SEED_MD,
            },
        )

        print(f"Seeded analysis {analysis_id} with artifact {artifact_id}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
