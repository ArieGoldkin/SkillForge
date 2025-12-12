# Golden Dataset Backups

This directory contains backup files for the SkillForge golden dataset.

## Files

| File | Size | Purpose |
|------|------|---------|
| `golden_dataset_backup.json` | ~1.4MB | **Primary backup** - Portable JSON format, version controlled |
| `golden_dataset_metadata.json` | ~600B | Quick stats without loading full backup |
| `golden_dataset_dump.sql` | ~9MB | SQL dump with vectors (gitignored, local only) |

## Backup Strategy

### JSON Backup (Recommended for Recovery)
- **Portable**: Works on any PostgreSQL instance
- **Version controlled**: Committed to git for safety
- **Vectors excluded**: Regenerated on restore (~2-3 min with OpenAI API)
- **Format**: Structured JSON with referential integrity

### SQL Dump (Local Full Backup)
- **Complete**: Includes vector embeddings
- **Fast restore**: No API calls needed
- **Not in git**: Too large, database-version specific

## Usage

```bash
# Create new backup
poetry run python scripts/backup_golden_dataset.py backup

# Verify backup integrity
poetry run python scripts/backup_golden_dataset.py verify

# Restore from backup (regenerates embeddings)
poetry run python scripts/backup_golden_dataset.py restore

# Restore and replace existing data
poetry run python scripts/backup_golden_dataset.py restore --replace

# Create SQL dump (local backup with vectors)
docker exec skillforge-postgres-dev pg_dump -U dev -d skillforge \
  --table=analyses --table=artifacts --table=analysis_chunks \
  --data-only --inserts > data/golden_dataset_dump.sql
```

## Current Dataset Stats

- **96 Analyses** (completed status)
- **96 Artifacts** (markdown implementation guides)
- **408 Chunks** (sections with embeddings)

### Content Types
- Articles: 76
- Tutorials: 19
- Research Papers: 1

## Recovery Procedures

### Scenario 1: Database wiped accidentally
```bash
cd backend
poetry run python scripts/backup_golden_dataset.py restore --replace
```

### Scenario 2: New development environment
```bash
cd backend
# Start database
docker compose up -d postgres

# Run migrations
poetry run alembic upgrade head

# Load golden dataset
poetry run python scripts/backup_golden_dataset.py restore
```

### Scenario 3: CI/CD database seeding
```bash
# In CI pipeline
poetry run python scripts/backup_golden_dataset.py restore --replace
```

## Related Files

- `scripts/backup_golden_dataset.py` - Backup/restore script
- `scripts/load_golden_dataset.py` - Initial data loader from fixtures
- `tests/smoke/retrieval/fixtures/documents_expanded.json` - Source documents
