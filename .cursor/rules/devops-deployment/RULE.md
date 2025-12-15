---
description: "CI/CD pipelines, containerization, Kubernetes, and infrastructure as code patterns"
alwaysApply: false
---

# devops-deployment

## Purpose

CI/CD pipelines, containerization, Kubernetes, and infrastructure as code patterns

## When to apply

- Apply when the task matches the capability keywords/triggers for this skill.
- If unsure, open `@.claude/skills/devops-deployment/capabilities.json` and check `capabilities.*.solves`.

Trigger hints from `capabilities.json` (keep this lightweight): `deploy.*to, ci.*cd.*setup, docker.*image, kubernetes.*deploy, pipeline, container`

## When NOT to apply

- If the task is unrelated to this skill’s domain and would add noise.
- If the baseline rule already fully covers the need (workflow/safety/evidence) and no specialized guidance is required.

## Do / Don’t (thin checklist)

- Do keep guidance **actionable** (short steps + clear outputs).
- Do open the skill’s `capabilities.json` first to confirm relevance before loading large references.
- Do use the skill’s `references/`, `templates/`, `checklists/`, and `examples/` as the source of truth.
- Do prefer pointing to files over copying large blocks into chat.
- Do tailor advice to the repo’s actual stack and constraints (don’t assume different frameworks).
- Do keep changes small and verifiable; add tests when behavior changes.
- Do preserve existing architecture patterns; don’t introduce new layers without justification.
- Don’t introduce new repo-wide policies here (those belong in `skillforge-baseline`).
- Don’t recommend unsafe commands or destructive operations without explicit user request.
- Don’t add dependencies casually; justify and document any new dependency.
- Don’t output long, ungrounded “best practices” essays—use checklists and references.
- Don’t proceed if the task needs a different skill—switch to the correct rule instead.

## Output contract

- Provide a short implementation outline referencing the relevant skill files used.
- Call out the specific files you changed/created.
- If you ran commands, include the command + exit code (or captured evidence).
- If you didn’t run commands, say what should be run to verify.

## Deep references (open only when needed)

- `@.claude/skills/devops-deployment/capabilities.json` (discovery + triggers)
- `@.claude/skills/devops-deployment/SKILL.md` (overview + patterns)
- Templates: `@.claude/skills/devops-deployment/templates/`
