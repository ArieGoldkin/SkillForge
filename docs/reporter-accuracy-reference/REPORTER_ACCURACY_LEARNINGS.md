# 📚 Reporter-Accuracy Learnings - Cursor Rules, Agents, Skills & MCPs

**Date:** November 20, 2025  
**Source:** Analysis of `../reporter-accuracy` project  
**Purpose:** Extract best practices for SkillForge setup

---

## 🎯 Executive Summary

Reporter-accuracy has a **sophisticated Claude Code setup** with:
- ✅ **13 specialized agents** (Opus + Sonnet models)
- ✅ **21 skills** (reusable patterns and templates)
- ✅ **8 MCP servers** (PostgreSQL, Playwright, Context7, etc.)
- ✅ **Comprehensive Cursor rules** (1000+ lines of standards)
- ✅ **GitHub-first workflow** (status awareness, atomic commits)
- ✅ **Domain-driven architecture** (file size limits, folder organization)

---

## 📋 1. Cursor Rules (.cursorrules)

### Key Sections

**1. Zero-Tolerance Execution Rules**
- Root cause analysis mandatory (never suppress warnings)
- Production ready = thoroughly tested
- Test verification mandatory (100% pass rate)
- Linting & type checks: 0 warnings, 0 errors
- Semantic Tailwind tokens only
- Async repository pattern + dependency injection

**2. GitHub Source of Truth**
- **MANDATORY:** GitHub is single source of truth
- Pre-work checklist (check issues, blockers, dependencies)
- During work updates (comment findings, blockers, status)
- Post-work documentation (implementation details, test evidence)
- Status refresh protocol (every 2 hours, before commits)

**3. Quality Gates**
- **Pre-commit:** Fast, selective (only changed files)
- **Pre-push:** Comprehensive (full test suite, coverage validation)
- Hard blocks: Backend ≥80%, Frontend ≥85% coverage
- Type errors: 0 type-arg errors, ≤50 backend, ≤30 frontend

**4. TypeScript & Code Quality**
- **NEVER use `any`** - use `unknown` or proper types
- **File size limits:** 200 lines (source), 300 lines (tests)
- **Folder size limits:** 15-30 files depending on type
- **Function complexity:** ≤5 parameters, ≤4 nesting levels
- **React hooks:** All dependencies declared, use `useCallback`/`useMemo`

**5. Domain-Driven Architecture**
- Domain boundaries (content, ml, analytics, notification)
- Infrastructure layer separation
- Migration rules (new code placement, legacy migration)
- Import rules (same domain relative, cross-domain absolute)

**6. Small Commits & Git Workflow**
- **MANDATORY:** Commit after each todo item
- Atomic commits (one logical change per commit)
- Quality gates before commit (automatic pre-commit hooks)
- Commit message format with Git trailers:
  ```
  Claude-Instance-Type: local-cli | cloud-web | github-action
  Claude-Instance-ID: <hostname>
  Claude-Session-ID: <unique-session>
  Agent: <agent-name>
  Agent-Task-ID: <todowrite-id>
  Issue: #<number>
  Milestone: <version>
  ```

---

## 🤖 2. Claude Agents (.claude/agents/)

### Agent Catalog (13 Agents)

| Agent | Model | Purpose | Cost |
|-------|-------|---------|------|
| **project-orchestrator** | Opus 4 | Break down multi-step tasks, delegate | $15/MTok |
| **backend-data-specialist** | Sonnet 4.5 | FastAPI, SQLAlchemy, Alembic | $3/MTok |
| **frontend-ui-specialist** | Sonnet 4.5 | React 19, TypeScript, Tailwind | $3/MTok |
| **testing-quality-specialist** | Sonnet 4.5 | pytest, Vitest, Playwright | $3/MTok |
| **ai-agent-specialist** | Opus 4 | LangGraph workflows, orchestration | $15/MTok |
| **ollama-specialist** | Sonnet 4.5 | Ollama operations, health checks | $3/MTok |
| **devops-infrastructure-specialist** | Sonnet 4.5 | Docker, CI/CD, deployment | $3/MTok |
| **documentation-specialist** | Sonnet 4.5 | Technical docs, API references | $3/MTok |
| **visual-design-specialist** | Opus 4 | Wireframes, diagrams, design | $15/MTok |
| **code-reviewer** | Sonnet 4.5 | Independent reviews, security | $3/MTok |
| **ml-service-specialist** | Opus 4 | PyTorch, NER, GPU optimization | $15/MTok |
| **api-gateway-specialist** | Sonnet 4.5 | Routing, auth, rate limiting | $3/MTok |
| **github-sprint-manager** | Sonnet 4.5 | Issue triage, sprint planning | $3/MTok |

### Delegation Rules

**Main Agent MUST NEVER:**
- ❌ GitHub operations → **devops-infrastructure-specialist**
- ❌ ML/NER code → **ml-service-specialist**
- ❌ Test writing → **testing-quality-specialist**
- ❌ LangGraph workflows → **ai-agent-specialist**
- ❌ Docker/CI/CD → **devops-infrastructure-specialist**

**Main Agent SHOULD:**
- ✅ Orchestrate and plan
- ✅ Break down complex tasks
- ✅ Delegate to specialists
- ✅ Coordinate between specialists
- ✅ Summarize results

### Agent File Structure

Each agent file (`.claude/agents/{agent-name}.md`) contains:
- Agent name, model, version
- Purpose and responsibilities
- When to use / when not to use
- Tools available (MCP servers, file operations)
- Quality gates and standards
- Example tasks and patterns

---

## 🎓 3. Skills (.claude/skills/)

### Skill Catalog (21 Skills)

**Backend & Infrastructure:**
- `fastapi-crud` - CRUD endpoints with repository pattern
- `alembic-migration` - Reversible migrations
- `docker-orchestration` - Multi-service Docker Compose
- `git-workflow` - Branch protection, PR conventions
- `langgraph-workflow` - StateGraph patterns, supervisor routing
- `ollama-operations` - Model lifecycle management
- `pytest-jest-suite` - Test templates and patterns

**Microservices & ML:**
- `ml-service-api` - ML endpoints, GPU optimization
- `api-gateway-routing` - Service routing, auth, rate limiting
- `microservice-contracts` - OpenAPI 3.0, contract testing
- `distributed-testing` - Service isolation, TestContainers

**Frontend:**
- `react-component-structure` - 5-file component scaffolding
- `react-query-hooks` - Query key factories, cache invalidation
- `shadcn-component` - shadcn/ui composition patterns
- `playwright-e2e` - Page Object Model, accessibility
- `sse-streaming-tests` - SSE integration testing

**Cross-Cutting:**
- `ascii-visualizer` - ASCII architecture diagrams
- `bilingual-llm-routing` - Hebrew/English detection
- `llm-testing` - Prompt suites, eval harnesses
- `security-audit` - OWASP Top 10, dependency scanning
- `hebrew-nlp` - Hebrew token handling, ML models

### Skill Structure

Each skill directory contains:
```
skill-name/
├── SKILL.md          # Main skill documentation
├── examples/         # Usage examples
├── templates/        # Code templates
├── reference/        # Reference guides
└── scripts/          # Helper scripts
```

**SKILL.md Format:**
```markdown
---
name: skill-name
description: Skill description
---

# Skill Name

🎯 SKILL ACTIVATION PROTOCOL
To use this skill, announce at the start:
🎯 Using {skill-name} skill for {purpose}

## Core Concepts
## Patterns
## Examples
## Templates
```

---

## 🔌 4. MCP Servers (.mcp.json)

### Configured MCP Servers (8 Total)

**1. sequential-thinking**
- Purpose: Structured reasoning for complex decisions
- Auto-invoked for architecture decisions
- Tools: `sequentialthinking`

**2. postgres-dev**
- Purpose: Query local PostgreSQL development DB (port 5435)
- Full access allowed (local dev only)
- Tools: Query, schema inspection, data manipulation

**3. postgres-test**
- Purpose: Query local PostgreSQL test DB (port 5436)
- Full access allowed (test environment)
- Tools: Schema inspection, test data verification

**4. playwright**
- Purpose: Browser automation for E2E tests
- Tools: `browser_navigate`, `browser_snapshot`, `browser_click`, etc.
- Prefer `browser_snapshot` over `browser_take_screenshot` (10x smaller tokens)

**5. vercel**
- Purpose: Vercel deployment platform management
- Read-only (no deploy/delete operations)
- Tools: `search_vercel_documentation`, `list_deployments`, `get_deployment_build_logs`

**6. google-cloud-observability**
- Purpose: Production monitoring (logs, metrics, traces)
- Tools: `list_log_entries`, `list_metric_descriptors`, `list_time_series`

**7. context7**
- Purpose: Library documentation access
- Tools: `resolve-library-id`, `get-library-docs`
- Distributed to 5 agents (backend, frontend, ai-agent, documentation, orchestrator)

**8. upstash**
- Purpose: Redis and QStash operations
- Tools: `redis_get`, `redis_set`, `qstash_publish_json`
- Require confirmation for: `redis_flushall`, `redis_flushdb`

### MCP Configuration Pattern

```json
{
  "$schema": "https://modelcontextprotocol.io/schema.json",
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["@package/server-name"],
      "description": "Purpose description",
      "alwaysAllow": ["tool1", "tool2"],
      "requireConfirmation": ["dangerous-tool"],
      "instructions": "Usage instructions for Claude"
    }
  },
  "agents": {
    "enabled": true,
    "directory": ".claude/agents",
    "autoDiscovery": true
  },
  "skills": {
    "enabled": true,
    "directory": ".claude/skills",
    "autoDiscovery": true,
    "contextOptimization": {
      "maxTokensPerTask": 85000,
      "enableProgressiveDisclosure": true,
      "unloadParentContext": true,
      "mainAgentMaxTokensPerTurn": 5000,
      "autoCompactThreshold": 150000
    }
  }
}
```

---

## 📁 5. Project Structure Patterns

### .claude/ Directory Structure

```
.claude/
├── agents/              # 13 specialist agents
│   ├── README.md       # Agent catalog
│   └── {agent-name}.md # Individual agent definitions
├── skills/             # 21 reusable skills
│   ├── {skill-name}/
│   │   ├── SKILL.md
│   │   ├── examples/
│   │   ├── templates/
│   │   └── reference/
├── instructions.md     # Auto-loaded Claude Code instructions
├── DELEGATION_RULES.md # Agent delegation patterns
├── UNIFIED_QUICK_REFERENCE.md # Shared agent + skill map
├── commands/           # Custom commands
├── generators/         # Code generators
├── hooks/              # Pre/post hooks
└── state/              # Session state
```

### Key Files

**CLAUDE.md** (Project Context Hub)
- Entry point for Claude Code
- Quick project overview
- Navigation to detailed docs
- Common workflows

**instructions.md** (Auto-loaded)
- Project snapshot
- Tech stack highlights
- Agent delegation rules
- Golden patterns
- Commit hygiene

**DELEGATION_RULES.md**
- What main agent MUST NEVER do
- What main agent SHOULD do
- Delegation decision tree
- Common patterns

---

## 🎯 6. Best Practices for SkillForge

### Recommended Setup

**1. Cursor Rules (.cursorrules)**
- Copy zero-tolerance execution rules
- Add GitHub source of truth protocol
- Include quality gates (pre-commit/pre-push)
- Add TypeScript/React standards
- Include file/folder size limits

**2. Claude Agents**
- Start with 5-7 core agents:
  - `project-orchestrator` (Opus)
  - `backend-data-specialist` (Sonnet)
  - `frontend-ui-specialist` (Sonnet)
  - `testing-quality-specialist` (Sonnet)
  - `ai-agent-specialist` (Opus) - for LangGraph
  - `devops-infrastructure-specialist` (Sonnet)
  - `documentation-specialist` (Sonnet)

**3. Skills**
- Start with essential skills:
  - `langgraph-workflow` (LangGraph v1.0 patterns)
  - `fastapi-crud` (FastAPI endpoints)
  - `react-component-structure` (React components)
  - `pytest-jest-suite` (Testing)
  - `alembic-migration` (Database migrations)

**4. MCP Servers**
- Essential servers:
  - `context7` (Library docs)
  - `sequential-thinking` (Complex reasoning)
  - `postgres-dev` (Local DB queries)
  - `playwright` (E2E testing)

**5. Project Structure**
- Create `.claude/` directory
- Add `CLAUDE.md` as entry point
- Add `instructions.md` for auto-loading
- Create `agents/` and `skills/` directories
- Add `.mcp.json` configuration

---

## 📊 7. Key Metrics & Standards

### Quality Gates
- Backend coverage: ≥80%
- Frontend coverage: ≥85%
- Type errors: 0 type-arg errors
- Linting: 0 warnings, 0 errors
- Tests: 100% pass rate

### File Size Limits
- Source files: 200 lines max
- Test files: 300 lines max
- Configuration: 100 lines max
- Documentation: 500 lines max

### Folder Size Limits
- Service folders: 15 files max
- API endpoints: 20 files max
- Test folders: 30 files max
- Schema folders: 25 files max

### Function Complexity
- Parameters: ≤5 per function
- Nesting depth: ≤4 levels
- Cyclomatic complexity: ≤15

---

## 🚀 8. Implementation Checklist for SkillForge

### Phase 1: Foundation
- [ ] Create `.cursorrules` file
- [ ] Create `CLAUDE.md` project hub
- [ ] Create `.claude/instructions.md`
- [ ] Create `.claude/DELEGATION_RULES.md`
- [ ] Create `.mcp.json` configuration

### Phase 2: Agents
- [ ] Create `.claude/agents/` directory
- [ ] Create 5-7 core agent files
- [ ] Create `agents/README.md` catalog
- [ ] Configure agent auto-discovery

### Phase 3: Skills
- [ ] Create `.claude/skills/` directory
- [ ] Create 5-7 essential skills
- [ ] Add examples and templates
- [ ] Configure skill auto-discovery

### Phase 4: MCP Servers
- [ ] Configure `context7` server
- [ ] Configure `sequential-thinking` server
- [ ] Configure `postgres-dev` server (if needed)
- [ ] Configure `playwright` server (for E2E)

### Phase 5: Documentation
- [ ] Create `UNIFIED_QUICK_REFERENCE.md`
- [ ] Document delegation patterns
- [ ] Add workflow examples
- [ ] Create quick start guide

---

## 📚 9. Key Takeaways

1. **GitHub-First Workflow**: Always check GitHub before starting work
2. **Atomic Commits**: Commit after each todo item, not at the end
3. **Agent Delegation**: Main agent orchestrates, specialists execute
4. **Quality Gates**: Hard blocks prevent regressions
5. **File Size Limits**: Enforce refactoring at 200 lines
6. **MCP Integration**: Use MCPs for database, docs, testing
7. **Skills Pattern**: Reusable patterns reduce duplication
8. **Context Optimization**: Progressive disclosure saves tokens

---

## 🔗 10. Reference Files

**From reporter-accuracy:**
- `.cursorrules` - Complete Cursor rules (1000+ lines)
- `.mcp.json` - MCP server configuration
- `CLAUDE.md` - Project context hub
- `.claude/instructions.md` - Auto-loaded instructions
- `.claude/DELEGATION_RULES.md` - Agent delegation patterns
- `.claude/UNIFIED_QUICK_REFERENCE.md` - Agent + skill catalog
- `.claude/agents/README.md` - Agent catalog
- `.claude/skills/langgraph-workflow/SKILL.md` - LangGraph skill example

---

**Document Status:** ✅ Complete Analysis  
**Next Action:** Implement Phase 1-5 for SkillForge

