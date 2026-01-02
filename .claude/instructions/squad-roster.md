# Squad Roster Configuration

## Overview

SkillForge uses **20 specialized agents** organized into squads:

| Squad | Agents | Purpose |
|-------|--------|---------|
| **Product Squad** | 6 | Strategy → Requirements → Metrics |
| **Architecture Squad** | 3 | System design, workflows |
| **Implementation Squad** | 5 | Frontend, backend, data |
| **Quality Squad** | 5 | Testing, security, debugging |
| **Research Squad** | 1 | User research |

---

## Product Squad (NEW)

**Purpose**: Product thinking pipeline before technical implementation

### market-intelligence
- **Model**: claude-3-sonnet
- **Color**: Violet
- **Token Limit**: 16,000
- **Specialization**: Competitive analysis, market sizing, SWOT, trends
- **Domain**: docs/research/**, docs/market/**
- **Tools**: Read, Write, WebSearch, WebFetch, Grep, Glob, Bash
- **Pipeline Position**: 1st (feeds product-strategist)

### product-strategist
- **Model**: claude-3-sonnet
- **Color**: Purple
- **Token Limit**: 16,000
- **Specialization**: Value proposition, go/no-go, build/buy/partner
- **Domain**: docs/strategy/**, docs/decisions/**
- **Tools**: Read, Write, WebSearch, WebFetch, Grep, Glob, Bash
- **Pipeline Position**: 2nd (receives from market-intelligence)

### prioritization-analyst
- **Model**: claude-3-sonnet
- **Color**: Plum
- **Token Limit**: 16,000
- **Specialization**: RICE/ICE/WSJF scoring, backlog ranking, opportunity cost
- **Domain**: docs/backlog/**, docs/priorities/**
- **Tools**: Read, Write, Grep, Glob, Bash
- **GitHub**: Issues, milestones, labels
- **Pipeline Position**: 3rd (receives from product-strategist)

### business-case-builder
- **Model**: claude-3-sonnet
- **Color**: Indigo
- **Token Limit**: 16,000
- **Specialization**: ROI, cost-benefit, sensitivity analysis, risk assessment
- **Domain**: docs/business-cases/**, docs/financials/**
- **Tools**: Read, Write, WebSearch, Grep, Glob, Bash
- **Pipeline Position**: 4th (receives from prioritization-analyst)

### requirements-translator
- **Model**: claude-3-sonnet
- **Color**: Magenta
- **Token Limit**: 16,000
- **Specialization**: PRDs, user stories, acceptance criteria, scope
- **Domain**: docs/requirements/**, docs/specs/**
- **Tools**: Read, Write, Grep, Glob, Bash
- **GitHub**: Issue creation with structured templates
- **Pipeline Position**: 5th (receives from business-case-builder)

### metrics-architect
- **Model**: claude-3-sonnet
- **Color**: Orchid
- **Token Limit**: 16,000
- **Specialization**: OKRs, KPIs, instrumentation, experiment design
- **Domain**: docs/metrics/**, docs/analytics/**
- **Tools**: Read, Write, Grep, Glob, Bash
- **Pipeline Position**: 6th (hands off to technical squads)

---

## Architecture Squad

### backend-system-architect
- **Model**: claude-3-sonnet
- **Token Limit**: 16,000
- **Specialization**: API design, database schemas, microservices, scalability
- **2026 Expertise**: Edge Computing, Streaming APIs, Type Safety (tRPC, Zod, Prisma), OpenTelemetry
- **Domain**: backend/**, api/**, database/**
- **Tools**: Read, Edit, MultiEdit, Write, Bash, Grep, Glob

### workflow-architect
- **Model**: claude-3-opus (complex reasoning)
- **Token Limit**: 32,000
- **Specialization**: LangGraph pipelines, supervisor-worker patterns, state management, checkpointing
- **Domain**: backend/app/workflows/**, backend/app/services/**
- **Tools**: Bash, Read, Write, Edit, Grep, Glob
- **MCP**: mcp__sequential-thinking, mcp__memory, mcp__context7

### system-design-reviewer
- **Model**: claude-3-sonnet
- **Token Limit**: 16,000
- **Specialization**: Architecture review, scalability analysis
- **Domain**: docs/architecture/**, docs/design/**
- **Tools**: Read, Grep, Glob

---

## Implementation Squad

### frontend-ui-developer
- **Model**: claude-3-sonnet
- **Instances**: 2 (parallel component work)
- **Token Limit**: 16,000
- **Specialization**: React 19, TypeScript, optimistic updates, concurrent features
- **2026 Expertise**: React Server Components, Next.js 15, Server Actions, Streaming SSR, Tailwind 4
- **Domain**: frontend/src/**, components/**, hooks/**
- **Tools**: Read, Edit, MultiEdit, Write, Bash, Grep, Glob

### rapid-ui-designer
- **Model**: claude-3-sonnet
- **Token Limit**: 16,000
- **Specialization**: UI mockups, Tailwind CSS, design systems, component specs
- **Domain**: designs/**, mockups/**, style-guides/**
- **Tools**: Write, Read, Grep, Glob
- **Never**: Writes implementation code

### database-engineer
- **Model**: claude-3-sonnet
- **Token Limit**: 16,000
- **Specialization**: PostgreSQL schemas, migrations, query optimization, pgvector
- **2026 Expertise**: PostgreSQL 18, UUID v7, TimescaleDB, full-text search
- **Domain**: backend/alembic/**, backend/app/db/**
- **Tools**: Bash, Read, Write, Edit, Grep, Glob
- **MCP**: mcp__pg-aiguide, mcp__postgres-mcp

### llm-integrator
- **Model**: claude-3-sonnet
- **Token Limit**: 16,000
- **Specialization**: LLM APIs (OpenAI, Anthropic, Ollama), prompts, function calling, streaming
- **Domain**: backend/app/services/llm/**, backend/app/prompts/**
- **Tools**: Bash, Read, Write, Edit, Grep, Glob, WebFetch

### data-pipeline-engineer
- **Model**: claude-3-sonnet
- **Token Limit**: 16,000
- **Specialization**: Embeddings, chunking strategies, vector indexes, data transformation
- **Domain**: backend/app/services/embedding/**, backend/app/services/chunking/**
- **Tools**: Bash, Read, Write, Edit, Grep, Glob

---

## Quality Squad

### code-quality-reviewer
- **Model**: claude-3-sonnet
- **Token Limit**: 16,000
- **Specialization**: Code review, linting, type checking, architectural compliance
- **Domain**: **/*.test.*, **/*.spec.*, tests/**
- **Tools**: Read, Bash, Grep, Glob
- **Never**: Implements features

### test-generator
- **Model**: claude-3-sonnet
- **Token Limit**: 16,000
- **Specialization**: Unit/integration tests, MSW mocking, VCR.py, test fixtures
- **Domain**: tests/**, **/*.test.*, **/*.spec.*
- **Tools**: Bash, Read, Write, Edit, Grep, Glob

### security-auditor
- **Model**: claude-3-sonnet
- **Token Limit**: 16,000
- **Specialization**: Vulnerability scanning, OWASP Top 10, secrets detection, dependency audit
- **Domain**: All code paths
- **Tools**: Bash, Read, Grep, Glob
- **Never**: Implements fixes (reports only)

### security-layer-auditor
- **Model**: claude-3-sonnet
- **Token Limit**: 16,000
- **Specialization**: Defense-in-depth review, security architecture
- **Domain**: All security-related code
- **Tools**: Read, Bash, Grep, Glob

### debug-investigator
- **Model**: claude-3-sonnet
- **Token Limit**: 16,000
- **Specialization**: Root cause analysis, error tracing, systematic debugging
- **Domain**: All code, logs, error traces
- **Tools**: Bash, Read, Grep, Glob

---

## Research Squad

### ux-researcher
- **Model**: claude-3-sonnet
- **Token Limit**: 16,000
- **Specialization**: Personas, user journeys, JTBD, usability validation
- **Domain**: research/**, personas/**, user-stories/**
- **Tools**: Write, Read, WebSearch, Grep, Glob
- **Never**: Implements solutions

---

## Agent Activation Rules

### Product Pipeline (Sequential)
```
market-intelligence → product-strategist → prioritization-analyst → business-case-builder → requirements-translator → metrics-architect
```
Activate sequentially for new feature evaluation.

### Phase-Based Activation

**Discovery Phase**:
- market-intelligence
- ux-researcher

**Strategy Phase**:
- product-strategist
- prioritization-analyst
- business-case-builder

**Requirements Phase**:
- requirements-translator
- metrics-architect
- ux-researcher

**Design Phase**:
- rapid-ui-designer
- backend-system-architect
- workflow-architect

**Implementation Phase**:
- frontend-ui-developer (1-2 instances)
- backend-system-architect
- database-engineer
- llm-integrator
- data-pipeline-engineer

**Quality Phase**:
- code-quality-reviewer
- test-generator
- security-auditor

**Debug Phase**:
- debug-investigator
- security-layer-auditor

---

## Parallel Execution Capabilities

### Can Run in Parallel
- frontend-ui-developer[1] + frontend-ui-developer[2] (different components)
- frontend-ui-developer + backend-system-architect (different layers)
- market-intelligence + ux-researcher (different research)
- test-generator + security-auditor (different concerns)
- Multiple read operations by any agents

### Must Run Sequentially
- Product pipeline agents (handoff dependencies)
- code-quality-reviewer → after implementation
- Same file modifications by different agents
- Integration testing → after all implementation

---

## Resource Limits

### Per Session
- **Max Active Agents**: 4 (excluding product pipeline)
- **Max Frontend Instances**: 2
- **Max Total Tokens**: 100,000 per session
- **Max Files Open**: 20 simultaneously

### Per Agent
- **Task Timeout**: 5 minutes
- **Max Retries**: 3 for blocked tasks
- **File Lock Duration**: 2 minutes max

---

## Model Selection Rationale

### Opus
- workflow-architect (complex multi-agent reasoning)

### Sonnet (All Others)
- Implementation tasks
- Code generation
- Design work
- Technical analysis
- Product strategy
- Research

---

## GitHub Integration

All product agents integrate with GitHub:

```bash
# Issues
gh issue list --milestone "v2.0" --json title,labels
gh issue create --title "..." --body "..." --label "feature"

# Milestones
gh milestone list --json title,dueOn

# Comments
gh issue view 123 --json comments
```

Key labels used:
- `priority::high`, `priority::medium`, `priority::low`
- `feature`, `bug`, `enhancement`
- `needs-prd`, `has-prd`, `ready-for-dev`
