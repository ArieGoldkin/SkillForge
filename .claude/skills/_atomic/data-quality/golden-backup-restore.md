---
name: golden-backup-restore
description: Backup and restore workflows for golden datasets
version: 1.0.0
tags: [golden-dataset, backup, restore, data-protection]
size: atomic
domain: data-quality
---

# Golden Dataset Backup & Restore

## Backup Strategy: JSON (Recommended)

**Pros:**
- Version controlled (commit to git)
- Human-readable (easy to inspect)
- Portable (works across DB versions)
- Incremental diffs (see what changed)

**Cons:**
- Must regenerate embeddings on restore
- Larger file size than SQL dump

## Backup Format

```json
{
  "version": "1.0",
  "created_at": "2025-12-19T10:30:00Z",
  "metadata": {
    "total_analyses": 98,
    "total_chunks": 415,
    "total_artifacts": 98
  },
  "analyses": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "url": "https://docs.python.org/3/library/asyncio.html",
      "content_type": "documentation",
      "status": "completed",
      "chunks": [
        {
          "id": "7c9e6679-...",
          "content": "asyncio is a library...",
          "section_title": "Introduction",
          "chunk_index": 0
          // embedding NOT included (regenerated on restore)
        }
      ]
    }
  ]
}
```

## Backup Implementation

```python
async def backup_golden_dataset():
    """Backup golden dataset to JSON."""

    async with get_session() as session:
        query = (
            select(Analysis)
            .where(Analysis.status == "completed")
            .order_by(Analysis.created_at)
        )
        result = await session.execute(query)
        analyses = result.scalars().all()

        backup_data = {
            "version": "1.0",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "total_analyses": len(analyses),
                "total_chunks": sum(len(a.chunks) for a in analyses),
            },
            "analyses": [serialize_analysis(a) for a in analyses]
        }

        with open(BACKUP_FILE, "w") as f:
            json.dump(backup_data, f, indent=2, default=str)

        print(f"✅ Backup: {len(analyses)} analyses")
```

## Restore with Embedding Regeneration

```python
async def restore_golden_dataset(replace: bool = False):
    """Restore golden dataset, regenerating embeddings."""

    with open(BACKUP_FILE) as f:
        backup_data = json.load(f)

    async with get_session() as session:
        if replace:
            await session.execute(delete(Chunk))
            await session.execute(delete(Analysis))
            await session.commit()

        from app.shared.services.embeddings import embed_text

        for analysis_data in backup_data["analyses"]:
            analysis = Analysis(
                id=UUID(analysis_data["id"]),
                url=analysis_data["url"],
                # ... other fields ...
            )
            session.add(analysis)

            for chunk_data in analysis_data["chunks"]:
                # Regenerate embedding with CURRENT model
                embedding = await embed_text(chunk_data["content"])

                chunk = Chunk(
                    id=UUID(chunk_data["id"]),
                    analysis_id=analysis.id,
                    content=chunk_data["content"],
                    embedding=embedding,  # Fresh!
                )
                session.add(chunk)

            await session.commit()
```

## CLI Usage

```bash
# Backup
poetry run python scripts/backup_golden_dataset.py backup

# Verify
poetry run python scripts/backup_golden_dataset.py verify

# Restore (WARNING: deletes existing)
poetry run python scripts/backup_golden_dataset.py restore --replace
```

## Best Practices

- **Version control backups** - Commit to git
- **Validate before deployment** - Run verify command
- **Test restore in staging** - Never test in production first
- **Regenerate embeddings** - Use current model on restore
