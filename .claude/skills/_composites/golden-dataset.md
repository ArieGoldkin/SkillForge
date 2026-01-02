---
name: golden-dataset
description: Complete golden dataset management - curation, backup, validation
version: 1.0.0
type: composite
includes:
  - data-quality/golden-classification
  - data-quality/golden-quality-dimensions
  - data-quality/golden-query-generation
  - data-quality/golden-backup-restore
  - data-quality/golden-schema-validation
  - data-quality/golden-duplicate-detection
trigger: "**/golden_dataset/**/*.py"
---

# Golden Dataset Management

Complete guide for curating, validating, and maintaining high-quality test datasets.

## When to Use

- Adding new documents to golden dataset
- Running backup/restore operations
- Validating data integrity
- Detecting duplicate content
- Analyzing coverage gaps

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    GOLDEN DATASET WORKFLOW                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  INPUT: URL/Content                                          │
│    │                                                         │
│    ▼                                                         │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐    │
│  │ DUPLICATE   │────▶│ QUALITY     │────▶│ CLASSIFY    │    │
│  │ DETECTION   │     │ EVALUATION  │     │ TYPE/DIFF   │    │
│  └─────────────┘     └─────────────┘     └─────────────┘    │
│         │                   │                   │           │
│         ▼                   ▼                   ▼           │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐    │
│  │ SCHEMA      │     │ QUERY       │     │ BACKUP      │    │
│  │ VALIDATION  │     │ GENERATION  │     │ RESTORE     │    │
│  └─────────────┘     └─────────────┘     └─────────────┘    │
│                             │                               │
│                             ▼                               │
│                      CURATED DATASET                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Included Skills

1. **golden-classification** - Content type + difficulty classification
2. **golden-quality-dimensions** - Accuracy, coherence, depth, relevance
3. **golden-query-generation** - Test query generation
4. **golden-backup-restore** - Backup/restore workflow
5. **golden-schema-validation** - Schema + integrity rules
6. **golden-duplicate-detection** - URL + semantic duplicates

## Quick Start: Add Document

```python
async def add_to_golden_dataset(url: str) -> dict:
    """Full curation workflow."""

    # 1. Fetch content
    content = await fetch_url(url)

    # 2. Check duplicates
    dup_check = await check_duplicates(url, content)
    if dup_check["has_duplicates"]:
        return {"error": dup_check["errors"]}

    # 3. Classify
    content_type = classify_content_type(content, url)
    difficulty = classify_difficulty(content)

    # 4. Evaluate quality
    quality = evaluate_quality(content)
    if quality["weighted_total"] < 0.70:
        return {"error": "Quality below threshold"}

    # 5. Generate queries
    queries = generate_test_queries(content, difficulty)

    # 6. Validate schema
    document = build_document(url, content, content_type, queries)
    validation = validate_schema(document)
    if not validation["valid"]:
        return {"error": validation["errors"]}

    # 7. Add to dataset
    await save_document(document)
    await backup_golden_dataset()

    return {"success": True, "document_id": document["id"]}
```

## CLI Commands

```bash
# Backup
poetry run python scripts/backup_golden_dataset.py backup

# Verify integrity
poetry run python scripts/backup_golden_dataset.py verify

# Restore (WARNING: deletes existing)
poetry run python scripts/backup_golden_dataset.py restore --replace

# Add new document
poetry run python scripts/data/add_to_golden_dataset.py add --url "https://..."

# Validate full dataset
poetry run python scripts/data/add_to_golden_dataset.py validate-all
```

## Quality Thresholds

| Dimension | Weight | Minimum |
|-----------|--------|---------|
| Accuracy | 0.25 | 0.70 |
| Coherence | 0.20 | 0.60 |
| Depth | 0.25 | 0.55 |
| Relevance | 0.30 | 0.70 |
| **Total** | 1.00 | **0.70** |

## SkillForge Stats

- **98 analyses** (completed content analyses)
- **415 chunks** (embedded text segments)
- **203 test queries** (with expected results)
- **91.6% pass rate** (retrieval quality metric)

## See Also

- [golden-classification](../_atomic/data-quality/golden-classification.md)
- [golden-quality-dimensions](../_atomic/data-quality/golden-quality-dimensions.md)
- [golden-query-generation](../_atomic/data-quality/golden-query-generation.md)
- [golden-backup-restore](../_atomic/data-quality/golden-backup-restore.md)
- [golden-schema-validation](../_atomic/data-quality/golden-schema-validation.md)
- [golden-duplicate-detection](../_atomic/data-quality/golden-duplicate-detection.md)
