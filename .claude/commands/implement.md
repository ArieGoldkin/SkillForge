---
description: Implement feature with parallel subagents, skills, and tests
---

Implement: $ARGUMENTS

## Step 1: Break Into Small Deliverable Tasks

Use TodoWrite to create specific, testable tasks:
- Each task should be completable in one focused session
- Each task MUST include its tests
- Group by domain (frontend, backend, shared)

## Step 2: Load Relevant Skills (Progressive Loading)

Check `.claude/skills/` for applicable knowledge:
```
1. Read capabilities.json first (~100 tokens)
2. Load only needed references/*.md or templates/*.md
3. Common skills: api-design-framework, testing-strategy-builder,
   streaming-api-patterns, type-safety-validation
```

## Step 3: Use MCPs for Current Documentation

Before implementing, fetch latest docs:
- `context7` → Get current library docs (React 19, FastAPI, etc.)
- `memory` → Load decisions from previous sessions
- `sequential-thinking` → For complex multi-step reasoning

## Step 4: Launch Parallel Subagents

For INDEPENDENT tasks, launch multiple subagents in ONE message:

```
Task(subagent_type="frontend-ui-developer", prompt="...", run_in_background=true)
Task(subagent_type="backend-system-architect", prompt="...", run_in_background=true)
```

Available subagents:
- `frontend-ui-developer` → React components, styling, hooks
- `backend-system-architect` → API endpoints, services, DB
- `ai-ml-engineer` → LLM integration, embeddings, RAG
- `code-quality-reviewer` → Lint, types, security, tests
- `Explore` → Codebase exploration and research

## Step 5: Sequential Dependent Tasks

After parallel work completes, run dependent tasks:
- Integration between frontend/backend
- End-to-end tests
- Quality review

## Step 6: Quality Gate

ALWAYS finish with:
```
Task(subagent_type="code-quality-reviewer", prompt="Review all changes:
- Run: cd backend && poetry run ruff format --check app/ && poetry run ruff check app/
- Run: cd frontend && npm run lint && npm run typecheck
- Run: cd backend && poetry run pytest tests/unit/ -v --tb=short
- Check for security issues
- Verify test coverage")
```

## Step 7: Update Context

- Mark TodoWrite tasks as completed
- Save decisions to memory MCP for future sessions

---

**Key Principles:**
- Tests are NOT optional - every task includes tests
- Parallel when independent, sequential when dependent
- Use skills for domain knowledge, MCPs for current docs
- Small deliverable tasks > large monolithic changes
