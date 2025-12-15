# Cursor Rules (generated from .claude/skills)

This directory mirrors `.claude/skills/*` into `.cursor/rules/*` as thin rules.

## How to use

- Baseline guardrails are always applied: `skillforge-baseline`.

- Most rules are designed to **Apply Intelligently** (Cursor decides via the rule `description`).

- Use `globs` only as a guardrail against irrelevant activation.

## Rules index

- `ai-native-development`: Apply Intelligently; globs: none
- `api-design-framework`: Apply Intelligently; globs: none
- `architecture-decision-record`: Apply Intelligently; globs: none
- `brainstorming`: Apply Intelligently; globs: none
- `code-review-playbook`: Apply Intelligently; globs: none
- `database-schema-designer`: Apply Intelligently; globs: none
- `design-system-starter`: Apply to Specific Files (globs present) / Apply Intelligently; globs: frontend/**/*.{ts,tsx}
- `devops-deployment`: Apply Intelligently; globs: none
- `edge-computing-patterns`: Apply Intelligently; globs: none
- `evidence-verification`: Apply Intelligently; globs: none
- `observability-monitoring`: Apply Intelligently; globs: none
- `performance-optimization`: Apply Intelligently; globs: none
- `quality-gates`: Apply Intelligently; globs: none
- `react-server-components-framework`: Apply to Specific Files (globs present) / Apply Intelligently; globs: frontend/**/*.{ts,tsx}
- `security-checklist`: Apply Intelligently; globs: none
- `streaming-api-patterns`: Apply Intelligently; globs: none
- `testing-strategy-builder`: Apply Intelligently; globs: none
- `type-safety-validation`: Apply Intelligently; globs: none

## Suggested validation prompts

- "Design a paginated FastAPI endpoint and error model" (expect: `api-design-framework` + baseline)

- "Implement SSE progress streaming and reconnection" (expect: `streaming-api-patterns` + baseline)

- "Add unit + integration tests for this new service" (expect: `testing-strategy-builder` + baseline)

- "Do a quick security pass for auth + input validation" (expect: `security-checklist` + baseline)

- "Create an ADR documenting a major architecture choice" (expect: `architecture-decision-record` + baseline)

- "Optimize a slow query / endpoint" (expect: `performance-optimization` + baseline)

- "Add structured logging + tracing hooks" (expect: `observability-monitoring` + baseline)

- "Design a migration + indexes" (expect: `database-schema-designer` + baseline)

- "Plan CI/CD deployment config" (expect: `devops-deployment` + baseline)

- "Brainstorm approaches and create a decision matrix" (expect: `brainstorming` + baseline)
