# Backend Scripts

This directory contains utility scripts for backend operations.

## Available Scripts

### 1. upload_datasets_to_langfuse.py

Upload golden evaluation datasets to Langfuse for experiment tracking and collaborative evaluation.

**Purpose:**
- Push golden datasets to Langfuse UI for visibility
- Enable dataset versioning and management
- Link experiment runs to datasets
- Enable collaborative evaluation workflows

**Prerequisites:**
```bash
# Set environment variables
export LANGFUSE_ENABLED=true
export LANGFUSE_PUBLIC_KEY=<your-public-key>
export LANGFUSE_SECRET_KEY=<your-secret-key>
export LANGFUSE_HOST=http://localhost:3000  # Optional, defaults to localhost
```

**Usage:**

```bash
# Upload all datasets
poetry run python scripts/upload_datasets_to_langfuse.py

# Upload specific dataset
poetry run python scripts/upload_datasets_to_langfuse.py --dataset supervisor

# Dry run (preview without uploading)
poetry run python scripts/upload_datasets_to_langfuse.py --dry-run

# Show help
poetry run python scripts/upload_datasets_to_langfuse.py --help
```

**Supported Datasets:**
- `supervisor` → `supervisor_routing_golden` (20 examples)
- `agent_analysis` → `agent_analysis_golden` (9 examples)
- `synthesis` → `synthesis_golden` (5 examples)

**Features:**
- Idempotent uploads (can run multiple times safely)
- Progress logging every 10 items
- Preserves dataset metadata from source files
- Error handling with detailed logs
- Dry-run mode for preview

**Output:**
```
2025-12-19 10:06:55 [info] upload_start datasets=['supervisor', 'agent_analysis', 'synthesis']
2025-12-19 10:06:55 [info] dataset_loaded dataset_name=supervisor example_count=20
2025-12-19 10:06:55 [info] dataset_created langfuse_name=supervisor_routing_golden
2025-12-19 10:06:55 [info] upload_progress uploaded=10 total=20 progress_pct=50.0
2025-12-19 10:06:55 [info] upload_complete uploaded=20 failed=0 success_rate=100.0
```

**Next Steps After Upload:**
1. Visit Langfuse UI: http://localhost:3000/datasets
2. Create experiment runs linked to datasets
3. Evaluate LLM outputs against golden examples
4. Track quality metrics over time

---

### 2. backup_golden_dataset.py

Backup and restore the golden dataset (98 production analyses).

**Usage:**
```bash
# Create backup
poetry run python scripts/backup_golden_dataset.py backup

# Verify backup integrity
poetry run python scripts/backup_golden_dataset.py verify

# Restore from backup
poetry run python scripts/backup_golden_dataset.py restore --replace
```

See main project CLAUDE.md for details on golden dataset protection.

---

## Development Guidelines

**When adding new scripts:**

1. Add docstring with purpose and usage examples
2. Use `argparse` for CLI arguments with `--help` support
3. Use structured logging via `app.core.logging.get_logger`
4. Handle errors gracefully with detailed error messages
5. Support dry-run mode where applicable
6. Document in this README

**Logging Best Practices:**
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# Use structured logging
logger.info(
    "operation_complete",
    items_processed=count,
    success_rate=rate,
)
```

**Error Handling:**
```python
try:
    result = operation()
except SpecificError as e:
    logger.error(
        "operation_failed",
        error=str(e),
        exc_info=True,  # Include stack trace
    )
    return 1  # Non-zero exit code
```
