---
description: "SkillForge baseline guardrails: workflow, safety, and evidence. Apply to every Cursor Agent session in this repo."
alwaysApply: true
---

# SkillForge baseline guardrails

## Scope

This rule applies to **all work** in this repository (backend, frontend, docs).

## Non-negotiables

- Do not suppress warnings, skip failing tests, or ignore type errors. Fix root cause.
- Do not commit directly to `dev` or `main`. Use a feature branch + PR.
- Do not leak secrets. Never paste API keys/tokens. Avoid logging sensitive values.
- Prefer small, verifiable steps with evidence (tests, lint/typecheck output).

## Project orientation (reference when needed)

When starting work on a new task, consider reading:

- `docs/CURRENT_STATUS.md` (what's in progress / blockers) - Read if working on sprint items
- `docs/ROADMAP.md` (big picture + phases) - Read if need full project context
- `.claude/context/shared-context.json` (prior decisions and evidence) - Read if working on related tasks

**Do NOT read these files automatically on every request** - only when they're relevant to the current task.

## Execution safety

- Avoid destructive commands unless explicitly requested (e.g., `rm -rf`, DB resets).
- If a command would be long-running, run it in the background.
- If you’re not sure whether a server is already running, check existing terminals first.

## Evidence expectations

When you change code, you should be able to show:

- Backend: formatting + lint + typecheck + tests (with coverage gates, per repo standards)
- Frontend: lint + typecheck + tests (per repo standards)

## Output expectations

When you finish a task:

- Summarize what changed and where (file paths).
- Provide evidence (commands run + exit codes) when applicable.













