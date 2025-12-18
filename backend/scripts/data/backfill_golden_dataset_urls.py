#!/usr/bin/env python3
"""Backfill golden dataset analyses URLs from fixture source_url.

This script fixes historical golden dataset rows that were seeded with placeholder
`*.skillforge.dev/<doc_id>` URLs by updating them to the real `source_url` stored
in the fixture file:

- backend/tests/smoke/retrieval/fixtures/documents_expanded.json

It also preserves the previous placeholder URL in `artifacts.artifact_metadata`
as `fixture_url`, and stores the new real URL as `source_url`.

Usage:
    poetry run python scripts/backfill_golden_dataset_urls.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()


class FixtureSourceUrlMissingError(ValueError):
    """Raised when a golden fixture document is missing its source_url."""


def _load_fixture_source_urls() -> dict[str, str]:
    fixtures_dir = Path(__file__).parent.parent / "tests/smoke/retrieval/fixtures"
    documents_path = fixtures_dir / "documents_expanded.json"
    data = json.loads(documents_path.read_text(encoding="utf-8"))
    docs = data["documents"]

    mapping: dict[str, str] = {}
    for doc in docs:
        doc_id = doc["id"]
        source_url = doc.get("source_url")
        if not source_url:
            msg = f"Missing source_url for fixture document id={doc_id}"
            raise FixtureSourceUrlMissingError(msg)
        mapping[doc_id] = source_url
    return mapping


async def main() -> int:
    """Run the backfill and print a summary."""
    from app.core.logging import get_logger
    from app.db.session import AsyncSessionLocal

    logger = get_logger(__name__)
    doc_id_to_source_url = _load_fixture_source_urls()

    placeholder_hosts = (
        "docs.skillforge.dev",
        "learn.skillforge.dev",
        "papers.skillforge.dev",
        "content.skillforge.dev",
    )

    # We only backfill rows that still use placeholder hosts.
    host_predicate = " OR ".join(
        ["url LIKE :h0"] + [f"url LIKE :h{i}" for i in range(1, len(placeholder_hosts))]
    )
    params = {f"h{i}": f"https://{h}/%" for i, h in enumerate(placeholder_hosts)}

    updated_analyses = 0
    updated_artifacts = 0
    skipped_unknown_doc_ids = 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                f"""
                SELECT id, url
                FROM analyses
                WHERE status = 'completed'
                  AND ({host_predicate})
                ORDER BY created_at
                """
            ),
            params,
        )
        rows = list(result.fetchall())

        for analysis_id, old_url in rows:
            # Extract doc_id as the first path segment after host.
            # Example: https://docs.skillforge.dev/context-engineering -> context-engineering
            try:
                doc_id = str(old_url).split("://", 1)[1].split("/", 1)[1].split("/", 1)[0]
            except Exception:
                logger.warning(
                    "golden_dataset_url_parse_failed", analysis_id=str(analysis_id), url=old_url
                )
                continue

            new_url = doc_id_to_source_url.get(doc_id)
            if not new_url:
                skipped_unknown_doc_ids += 1
                logger.warning(
                    "golden_dataset_doc_id_not_in_fixture",
                    analysis_id=str(analysis_id),
                    doc_id=doc_id,
                    url=old_url,
                )
                continue

            if old_url == new_url:
                continue

            await session.execute(
                text("UPDATE analyses SET url = :new_url WHERE id = :analysis_id"),
                {"analysis_id": analysis_id, "new_url": new_url},
            )
            updated_analyses += 1

            artifact_result = await session.execute(
                text(
                    """
                    UPDATE artifacts
                    SET artifact_metadata =
                      jsonb_set(
                        jsonb_set(
                          COALESCE(artifact_metadata, '{}'::jsonb),
                          '{fixture_url}',
                          to_jsonb(CAST(:old_url AS text)),
                          true
                        ),
                        '{source_url}',
                        to_jsonb(CAST(:new_url AS text)),
                        true
                      )
                    WHERE analysis_id = :analysis_id
                    """
                ),
                {"analysis_id": analysis_id, "old_url": old_url, "new_url": new_url},
            )
            updated_artifacts += int(artifact_result.rowcount or 0)

        await session.commit()

    logger.info(
        "golden_dataset_url_backfill_complete",
        analyses_scanned=len(rows),
        analyses_updated=updated_analyses,
        artifacts_updated=updated_artifacts,
        skipped_unknown_doc_ids=skipped_unknown_doc_ids,
    )

    print("Backfill complete")
    print(f"  Analyses scanned:  {len(rows)}")
    print(f"  Analyses updated:  {updated_analyses}")
    print(f"  Artifacts updated: {updated_artifacts}")
    print(f"  Skipped unknown doc_ids: {skipped_unknown_doc_ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
