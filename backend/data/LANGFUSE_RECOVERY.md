# Langfuse Recovery Quick Reference

## Emergency Recovery (Container Rebuilt)

If Langfuse container was rebuilt and you lost all prompts/configs:

### Step 1: Restore Prompts (Automatic)

```bash
cd backend

LANGFUSE_ENABLED=true \
LANGFUSE_PUBLIC_KEY=pk-lf-0ccec7b6-89cc-4174-83f0-511bb3f7b5ce \
LANGFUSE_SECRET_KEY=sk-lf-e96cdcaf-74ff-47b6-90a3-ff0427635322 \
LANGFUSE_HOST=http://localhost:3000 \
poetry run python scripts/backup_langfuse.py restore
```

### Step 2: Restore Score Configs (Manual)

Open http://localhost:3000 → Settings → Scores → Add Score Config:

| Name | Type | Min | Max | Description |
|------|------|-----|-----|-------------|
| quality | NUMERIC | 0 | 10 | G-Eval quality score for analysis depth and accuracy |
| depth_score | NUMERIC | 0 | 10 | Analysis depth score |
| accuracy_score | NUMERIC | 0 | 10 | Technical accuracy score |
| relevance_score | NUMERIC | 0 | 10 | Relevance to user goals score |
| coherence_score | NUMERIC | 0 | 10 | Output coherence score |

### Step 3: Restore LLM Connections (Manual)

Open http://localhost:3000 → Settings → LLM API Keys:

1. **OpenAI** - Add API key from backend/.env → `OPENAI_API_KEY`
2. **Anthropic** - Add API key from backend/.env → `ANTHROPIC_API_KEY`
3. **Google** - Add API key from backend/.env → `GOOGLE_API_KEY`

## Verify Recovery

```bash
# Check that all 10 prompts were restored
cd backend
LANGFUSE_ENABLED=true \
LANGFUSE_PUBLIC_KEY=pk-lf-0ccec7b6-89cc-4174-83f0-511bb3f7b5ce \
LANGFUSE_SECRET_KEY=sk-lf-e96cdcaf-74ff-47b6-90a3-ff0427635322 \
LANGFUSE_HOST=http://localhost:3000 \
poetry run python scripts/backup_langfuse.py verify
```

Expected output:
```
✓ Prompts: prompts_backup.json (count: 10)
✓ Score Configs: score_configs_backup.json (count: 5)
✓ LLM Connections: llm_connections_backup.json (count: 3)
```

## Backup Before Changes

Always backup before major changes:

```bash
cd backend

LANGFUSE_ENABLED=true \
LANGFUSE_PUBLIC_KEY=pk-lf-0ccec7b6-89cc-4174-83f0-511bb3f7b5ce \
LANGFUSE_SECRET_KEY=sk-lf-e96cdcaf-74ff-47b6-90a3-ff0427635322 \
LANGFUSE_HOST=http://localhost:3000 \
poetry run python scripts/backup_langfuse.py backup
```

## Files Location

- Backup script: `backend/scripts/backup_langfuse.py`
- Backups directory: `backend/data/langfuse_backups/`
- Full documentation: `backend/data/langfuse_backups/README.md`

## Troubleshooting

### "Failed to connect to Langfuse"
- Check container: `docker compose ps langfuse-web`
- Start if stopped: `docker compose up -d langfuse-web`
- Wait for healthy: `docker compose ps` (should show "healthy")

### "Authentication failed"
- Verify API keys in backend/.env
- Check LANGFUSE_HOST is http://localhost:3000 (not docker network hostname)

### Prompts show as empty
- This is expected - prompt content is in application code
- Names, versions, and labels are preserved for tracking

## API Credentials (Local Dev Only)

```bash
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-0ccec7b6-89cc-4174-83f0-511bb3f7b5ce
LANGFUSE_SECRET_KEY=sk-lf-e96cdcaf-74ff-47b6-90a3-ff0427635322
```

**DO NOT use these in production!**
