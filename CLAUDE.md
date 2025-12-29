# SkillForge

AI-powered learning platform with multi-agent content analysis via LangGraph.

## Stack
- **Backend**: FastAPI + LangGraph 1.0 + PostgreSQL/PGVector
- **Frontend**: React 19 + TypeScript + Vite
- **Ports**: Frontend `:5173` | Backend `:8500` | Postgres `:5437`

## Commands
```bash
# Backend
cd backend && poetry run pytest tests/unit/ -v --tb=short    # Tests
cd backend && poetry run ruff format --check app/ && poetry run ruff check app/  # Lint
cd backend && poetry run ty check app/ --exclude "app/evaluation/*"  # Types

# Frontend
cd frontend && npm run format:check && npm run lint && npm run typecheck
```

## Workflow
- **ALWAYS** create feature branches: `issue/<number>-<description>`
- **NEVER** commit to dev/main directly (hooks will block)
- Run ALL checks before committing (format + lint + types)

## Key Directories
```
backend/app/workflows/     # LangGraph agent workflows
backend/app/api/           # FastAPI endpoints
backend/app/services/      # Business logic
frontend/src/features/     # Feature-based React components
docs/                      # Architecture and task specs
```

## Context Files (Read as needed)
| File | Purpose |
|------|---------|
| `.claude/instructions/context-initialization.md` | New session protocol |
| `docs/CURRENT_STATUS.md` | Sprint progress |
| `docs/KNOWN_BUGS.md` | Historical bug fixes |
| `docs/ARCHITECTURE.md` | System design |
| `.claude/context/shared-context.json` | Cross-session decisions |

## Skills & Agents
27 skills in `.claude/skills/` with progressive loading via `capabilities.json`.
10 agents in `.claude/agents/` for specialized tasks.

Use `context7` MCP for current library docs before implementing.

## Golden Dataset
98 curated documents for semantic search testing.
```bash
cd backend && poetry run python scripts/backup_golden_dataset.py verify
```

---
*v4.3.0 (Dec 2025) - Refactored for <60 lines per industry best practices*
