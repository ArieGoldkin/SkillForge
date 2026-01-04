# Langfuse Configuration Backups

This directory contains version-controlled backups of all Langfuse configurations to prevent data loss during container rebuilds.

## Contents

| File | Description | Auto-Restore |
|------|-------------|--------------|
| `prompts_backup.json` | 10 agent prompts (supervisor + 9 analysis agents) | ✅ Yes |
| `score_configs_backup.json` | 5 G-Eval score configurations | ❌ Manual |
| `llm_connections_backup.json` | 3 LLM provider connections | ❌ Manual |
| `datasets_backup.json` | Datasets (currently none) | ✅ Yes |
| `backup_metadata.json` | Backup timestamp and counts | N/A |

## Backup Commands

```bash
cd backend

# Create backup (run before container rebuild)
LANGFUSE_ENABLED=true \
LANGFUSE_PUBLIC_KEY=pk-lf-0ccec7b6-89cc-4174-83f0-511bb3f7b5ce \
LANGFUSE_SECRET_KEY=sk-lf-e96cdcaf-74ff-47b6-90a3-ff0427635322 \
LANGFUSE_HOST=http://localhost:3000 \
poetry run python scripts/backup_langfuse.py backup

# Verify backup integrity
poetry run python scripts/backup_langfuse.py verify

# Restore after container rebuild
LANGFUSE_ENABLED=true \
LANGFUSE_PUBLIC_KEY=<your-key> \
LANGFUSE_SECRET_KEY=<your-secret> \
LANGFUSE_HOST=http://localhost:3000 \
poetry run python scripts/backup_langfuse.py restore
```

## Restore Methods

Two restore methods are available:

### Option A: API Restore (JSON/API) - Default

**Description:** Uses Langfuse API to restore prompts, score_configs, datasets  
**Script:** `backend/scripts/backup_langfuse.py restore`  
**Advantages:**
- Simpler, safer for most use cases
- No direct database access required
- Easier to debug

**Usage:** See "Recovery After Container Rebuild" section below

### Option B: SQL Restore (Database Direct)

**Description:** Direct PostgreSQL database restore from SQL backup  
**Scripts:** 
- `backend/scripts/extract_langfuse_config_tables.py` - Filters SQL backup
- `backend/scripts/restore_langfuse_db_filtered.py` - Restores filtered backup

**Advantages:**
- Faster (single SQL restore vs multiple API calls)
- More complete (includes datasets, annotation_queues automatically)
- Preserves all config tables

**Requirements:**
- SQL backup file (see `backend/data/langfuse_db_backups/`)
- Direct database access (Docker container)

**Usage:**
```bash
cd backend

# Restore filtered SQL backup
poetry run python scripts/restore_langfuse_db_filtered.py \
  --backup data/langfuse_db_backups/latest.sql \
  --container skillforge-langfuse-db-test
```

**For automatic restore:** Set `LANGFUSE_RESTORE_METHOD=sql` in `.env.test`

**See:** `docs/LANGFUSE_SQL_RESTORE_PLAN.md` for detailed documentation

| Aspect | Option A (API) | Option B (SQL) |
|--------|---------------|----------------|
| **Completeness** | Partial (prompts, score_configs) | Complete (all config tables) |
| **Datasets** | ❌ Not restored | ✅ Restored |
| **Annotation Queues** | ❌ Manual setup | ✅ Restored |
| **Speed** | Slower (multiple API calls) | Faster (single SQL restore) |
| **Safety** | ✅ Very safe (no data risk) | ⚠️ Requires filtering |
| **When to Use** | Default for most cases | When you need complete config restore |

## Recovery After Container Rebuild

Two restore methods are available (see "Restore Methods" section above).

### Option A: API Restore (Recommended for most cases)

1. Ensure Langfuse container is running:
   ```bash
   docker compose up -d langfuse-web
   ```

2. Run restore script:
   ```bash
   cd backend
   LANGFUSE_ENABLED=true \
   LANGFUSE_PUBLIC_KEY=pk-lf-0ccec7b6-89cc-4174-83f0-511bb3f7b5ce \
   LANGFUSE_SECRET_KEY=sk-lf-e96cdcaf-74ff-47b6-90a3-ff0427635322 \
   LANGFUSE_HOST=http://localhost:3000 \
   poetry run python scripts/backup_langfuse.py restore
   ```

### Option B: SQL Restore (For complete config restore)

1. Ensure Langfuse database container is running:
   ```bash
   docker compose up -d langfuse-db
   ```

2. Run SQL restore script:
   ```bash
   cd backend
   poetry run python scripts/restore_langfuse_db_filtered.py \
     --backup data/langfuse_db_backups/latest.sql \
     --container skillforge-langfuse-db-test
   ```

**Note:** SQL restore requires a SQL backup file. See `backend/data/langfuse_db_backups/README.md` (if exists) or `docs/LANGFUSE_SQL_RESTORE_PLAN.md` for SQL backup creation.

### Manual Recovery (Score Configs)

Score configurations must be recreated manually in Langfuse UI.

**Reference:** `score_configs_backup.json`

**Steps:**
1. Open Langfuse UI: http://localhost:3000
2. Go to **Settings → Scores**
3. Click **Add Score Config** for each:

| Name | Type | Range | Description |
|------|------|-------|-------------|
| `quality` | NUMERIC | 0-10 | G-Eval quality score for analysis depth and accuracy |
| `depth_score` | NUMERIC | 0-10 | Analysis depth score |
| `accuracy_score` | NUMERIC | 0-10 | Technical accuracy score |
| `relevance_score` | NUMERIC | 0-10 | Relevance to user goals score |
| `coherence_score` | NUMERIC | 0-10 | Output coherence score |

### Manual Recovery (LLM Connections)

LLM API keys should NOT be committed to git. This file documents the required connections only.

**Reference:** `llm_connections_backup.json`

**Steps:**
1. Open Langfuse UI: http://localhost:3000
2. Go to **Settings → LLM API Keys**
3. Add each provider:

| Provider | Model | Use Case |
|----------|-------|----------|
| OpenAI | gpt-4o-mini | Main agent LLM (cost efficiency) |
| Anthropic | claude-3-5-sonnet-20241022 | High-quality analysis |
| Google | gemini-2.0-flash-exp | G-Eval quality scoring |

**IMPORTANT:** Use API keys from your `.env` file, NOT the backup file!

## Backup Schedule

- **Before container rebuild:** Always run backup
- **After major changes:** Run backup after adding/modifying prompts
- **Weekly:** Automated backup recommended for production

## Current Backup Status

```json
{
  "backup_timestamp": "2025-12-21T07:47:02.677129+00:00",
  "langfuse_host": "http://localhost:3000",
  "prompts_count": 10,
  "datasets_count": 0,
  "score_configs_count": 5,
  "llm_connections_count": 3
}
```

## API Credentials

**Current Langfuse credentials** (local development only):
- Host: http://localhost:3000
- Public Key: `pk-lf-0ccec7b6-89cc-4174-83f0-511bb3f7b5ce`
- Secret Key: `sk-lf-e96cdcaf-74ff-47b6-90a3-ff0427635322`

**IMPORTANT:** These are for the local Langfuse instance only. Do NOT use in production.

## Troubleshooting

### Restore fails with "prompt already exists"
- This is expected - the script will skip existing prompts
- Manually delete conflicting prompts in Langfuse UI if you need to force restore

### Authentication fails
- Verify container is running: `docker compose ps langfuse-web`
- Check API keys match your `.env` file
- Ensure `LANGFUSE_HOST=http://localhost:3000` (not docker network hostname)

### Prompts are empty
- The backup shows empty prompts because the prompt content is stored in the database but not exposed via the API list endpoint
- The prompt names, versions, and labels are preserved, which is sufficient for tracking
- Actual prompt content is managed in the application code, not in Langfuse

## See Also

- **Option A (API Restore):**
  - Backup script: `backend/scripts/backup_langfuse.py`
  - Setup scripts: `setup_langfuse_score_configs.py`, `setup_langfuse_annotation_queue.py`

- **Option B (SQL Restore):**
  - Extract script: `backend/scripts/extract_langfuse_config_tables.py`
  - Restore script: `backend/scripts/restore_langfuse_db_filtered.py`
  - Detailed documentation: `docs/LANGFUSE_SQL_RESTORE_PLAN.md`

- **General:**
  - Langfuse documentation: https://langfuse.com/docs
  - Langfuse observability skill: `.claude/skills/langfuse-observability/SKILL.md`
