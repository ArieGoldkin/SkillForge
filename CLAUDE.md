---
name: claude-main
description: AI Agent Hub - Modular Intelligence System
version: 4.0.0
---

# 🚀 AI Agent Hub - Intelligent Orchestration

**Mode**: ⚡ Squad (Parallel) | **Discovery**: 🔍 Dynamic MCP (v4.0)

## 🔄 MANDATORY: New Context Window Initialization

**EVERY TIME a new conversation/context window starts, YOU MUST:**

1. **Read** `.claude/instructions/context-initialization.md` for the full protocol
2. **Execute** the initialization steps before doing any work

**Quick Summary (read full protocol for details):**
- Read `docs/CURRENT_STATUS.md` → Sprint progress, blockers, completed work
- Read `docs/ROADMAP.md` → Tech stack, phases, task breakdown
- Read `.claude/context/shared-context.json` → Decisions from previous sessions
- Check `git log --oneline -10` and `git status` → Recent changes

**Full Protocol:** `.claude/instructions/context-initialization.md`

---

## 📦 Project: SkillForge

**Intelligent Learning Integration Platform** - Multi-agent system that analyzes technical content (URLs, videos, repos) via LangGraph pipeline and generates AI-ready implementation guides with Socratic tutoring.

**Stack**: React 19 + FastAPI + LangGraph 1.0 + PostgreSQL/PGVector

**Development Ports** (docker-compose.yml):
- Frontend: `localhost:5173` (Vite dev server)
- Backend API: `localhost:8500` (FastAPI/Uvicorn)
- PostgreSQL: `localhost:5437` (mapped from container's 5432)

**Architecture**:
- System design: `docs/ARCHITECTURE.md` (workflows, deployment, diagrams)
- Agent coordination: `.claude/instructions/architecture-decisions.md` (file-based, supervisor-worker)

**Docs**:
- Overview: `README.md` | `docs/USER_STORIES.md`
- Integration: `docs/INTEGRATION_POINTS.md`
- Tasks: `docs/ARIE_FRONTEND_TASKS.md` | `docs/YONATAN_BACKEND_TASKS.md`

**Key Design Decisions**:
- File-based agent communication (no APIs/DBs) → `.squad/sessions/`
- Parallel execution via domain isolation → See `.claude/instructions/parallel-execution-rules.md`
- 8 specialized content analysis agents → Tech Comparator, Security Auditor, Implementation Planner, etc.
- Evidence-based verification (exit codes, test logs) → Quality gates at 80%+ coverage

**Codebase Structure**: `backend/` (FastAPI + LangGraph) | `frontend/` (React 19) | `docs/` (specs & tasks)


## 🐛 Known Bugs & Fixes (Historical Reference)

### SSE Race Condition (Fixed Dec 2024)
- **Problem**: Frontend shows 0% progress, "Waiting for agent activity..." while backend runs
- **Root Cause**: EventBroadcaster had no buffering - events published before SSE subscriber connects were lost
- **Fix**: Added event buffering with `deque(maxlen=100)` per channel, events replayed to new subscribers
- **Location**: `backend/app/services/event_broadcaster.py`
- **Tests**: `backend/tests/unit/test_event_broadcaster.py` (5 buffer tests)

### Quality Gate ValidationError (Fixed Dec 2024)
- **Problem**: `pydantic.v1.error_wrappers.ValidationError: 3 validation errors for Run`
- **Root Cause**: LangSmith `Run` schema requires `start_time` and `trace_id` fields
- **Fix**: Added `start_time=datetime.now(UTC)` and `trace_id=uuid4()` to mock Run object
- **Location**: `backend/app/workflows/nodes/quality_gate_node.py` lines 102-129

### Workflow Timeout (Configured Dec 2024)
- **Problem**: Workflow times out during multi-agent execution
- **Fix**: Increased `STEP_TIMEOUT` from 90s to 300s (5 minutes)
- **Location**: `backend/app/core/timeout_config.py`


## 📋 Development Standards (MUST FOLLOW)

1. **ALWAYS add/update tests** before running real analysis
2. **ALWAYS use Claude subagents and skills** for specialized tasks (Explore, Plan, code-quality-reviewer, etc.)
3. **Run lint checks** (`ruff format --check`, `ruff check`, `ty check`) before committing
4. **Use TodoWrite** to track multi-step tasks
5. **Never commit directly** to dev/main - always use feature branches + PRs

## 🧪 Testing Standards (MANDATORY)

**ALWAYS run tests with live progress output that the user can watch:**

```bash
# Backend tests - with live progress log
cd backend
poetry run pytest tests/unit/ --tb=short -v 2>&1 | tee /tmp/test_results.log | grep -E "(PASSED|FAILED|ERROR|===|test session|passed|failed)" | tail -50

# Or for full output:
poetry run pytest tests/unit/ --tb=short -v 2>&1 | tee /tmp/test_results.log

# Quick summary:
poetry run pytest tests/unit/ --tb=no -q 2>&1 | tail -20
```

**Key Requirements:**
- **ALWAYS use `tee`** to save output to `/tmp/test_results.log` for later review
- **ALWAYS use `-v` (verbose)** or `-q` (quiet) - never silent
- **ALWAYS show progress** - use `grep` filters or `tail` to show recent activity
- **NEVER run tests without visible output** - user needs to see progress
- **For long-running tests**, use `--maxfail=5` to stop after first few failures

**Test Output Patterns:**
- `tee /tmp/test_results.log` - Saves full log for analysis
- `grep -E "(PASSED|FAILED|ERROR)"` - Shows only test results
- `tail -50` - Shows last 50 lines (recent activity)
- `--tb=short` - Shorter tracebacks (faster output)
- `--tb=no` - No tracebacks (fastest, summary only)


## 🚨 CRITICAL: Pre-Commit Validation (NEVER SKIP)

**BEFORE every commit or PR, you MUST run ALL CI checks locally:**

```bash
# Backend (Python) - from backend/ directory:
cd backend
poetry run ruff format --check app/  # ⚠️ CI runs BOTH format AND lint!
poetry run ruff check app/           # Lint check
poetry run ty check app/ --exclude "app/evaluation/*"  # Type check (ty - Rust-based)

# Frontend (TypeScript) - from frontend/ directory:
cd frontend
npm run lint               # ENTIRE codebase
npm run typecheck          # Type checking
```

**Why this matters:**
- CI runs BOTH `ruff format --check` AND `ruff check` - running only one will miss issues!
- CI runs lint on the FULL codebase, not just changed files
- Changing one file can cause lint errors in importing files

**Common mistakes to NEVER make:**
- ❌ Running only `ruff check` without `ruff format --check`
- ❌ `ruff check app/services/embeddings.py` (only checks one file)
- ✅ Run ALL three commands above (format, lint, ty check)


## 🛑 ABSOLUTE: Git Branch & PR Workflow (NEVER VIOLATE)

**THIS IS NON-NEGOTIABLE. VIOLATING THIS WORKFLOW IS A CRITICAL FAILURE.**

### The Rule
**NEVER commit directly to `dev` or `main` branches. ALWAYS use feature branches + PRs.**

### Required Workflow
```bash
# 1. Create feature branch from dev (ALWAYS)
git checkout dev
git pull origin dev
git checkout -b issue/<issue-number>-<brief-description>

# 2. Do your work, commit to feature branch
git add .
git commit -m "feat(#<issue>): Description"

# 3. Push feature branch
git push -u origin issue/<issue-number>-<brief-description>

# 4. Create PR to dev (NEVER skip this)
gh pr create --base dev --head issue/<issue-number>-<brief-description> --title "..." --body "..."
```

### Branch Naming Convention
- `issue/<number>-<description>` - For GitHub issues (e.g., `issue/273-golden-dataset-expansion`)
- `feature/<description>` - For features without issues
- `fix/<description>` - For bug fixes without issues

### FORBIDDEN Actions (Will cause rollback + shame)
- ❌ `git commit` while on `dev` branch
- ❌ `git commit` while on `main` branch
- ❌ `git push origin dev` with new commits
- ❌ `git push origin main` with new commits
- ❌ Skipping PR creation after feature work

### Pre-Commit Branch Check
**BEFORE any commit, ALWAYS verify:**
```bash
# Check current branch - if dev or main, STOP and create feature branch
git branch --show-current
```

### If You Accidentally Commit to dev/main
```bash
# 1. Create feature branch at current commit
git checkout -b issue/<number>-<description>

# 2. Reset dev/main to remote state
git checkout dev
git reset --hard origin/dev

# 3. Push feature branch and create PR
git checkout issue/<number>-<description>
git push -u origin issue/<number>-<description>
gh pr create --base dev ...
```

**Remember: PRs enable code review, CI checks, and audit trails. Direct commits bypass all safety nets.**


## 📋 Modular Instruction System

This project uses specialized instruction files to optimize tokens while maintaining agent capabilities.

**YOU MUST** follow the agent activation protocol below for every task.

### 📁 Available Instruction Files

| File | Contains |
|------|----------|
| `.claude/instructions/context-initialization.md` | **NEW CONTEXT WINDOW PROTOCOL** - Must read first |
| `.claude/instructions/orchestration.md` | Agent routing & coordination rules |
| `.claude/instructions/agents.md` | Full agent capabilities & specializations |
| `.claude/instructions/context.md` | Context persistence system details |
| `.claude/instructions/workflows.md` | Multi-step project patterns |
| `.claude/instructions/context-middleware.md` | Context protocol (load when using agents) |
| `.claude/instructions/cli-integration.md` | Claude Code CLI behavior |
| `.claude/instructions/super-design.md` | UI/frontend design workflow & tools |
| `.claude/instructions/supervisor-rules.md` | Squad supervisor orchestration rules |
| `.claude/instructions/squad-roster.md` | Agent assignments & capabilities |
| `.claude/instructions/communication-protocol.md` | File-based messaging protocol |
| `.claude/instructions/parallel-execution-rules.md` | Conflict prevention & locking |
| `.claude/instructions/architecture-decisions.md` | Shared architectural context |


## ⚡ MANDATORY: Agent Activation Protocol (v4.0 - Dynamic Discovery)

**BEFORE responding to ANY user task, YOU MUST execute this protocol:**

### Step 1: Dynamic Agent Discovery (NEW in v4.0)
1. **Read** `.claude/agent-registry.json` for semantic capability matching
2. **Match** user intent against `agent.can_solve_examples` (not just keywords)
3. **Check** `.claude/workflows/` for pre-composed solutions
4. **Score** confidence (0-1) and select agents above 0.7 threshold

### Step 2: Progressive Skill Loading (NEW in v4.0)
**CRITICAL**: Never load full SKILL.md files when only specific guidance is needed.
1. **First**: Read `capabilities.json` (~100 tokens) to find relevant capability
2. **Then**: Load only the specific `references/*.md` or `templates/*.md` needed
3. **Token savings**: 60-80% vs loading full skills

### Step 3: Check Pre-Composed Workflows
**BEFORE ad-hoc coordination**, check `.claude/workflows/`:
- `secure-api-endpoint.md` - API with auth, validation, tests
- `full-stack-feature.md` - Backend + Frontend with shared types
- `ai-integration.md` - LLM streaming, observability, cost tracking

### Step 4: MCP Tool Integration
**ALWAYS use MCP tools during development:**
- `context7` → Fetch current library documentation before implementing
- `mcp-find` → Discover additional tools as needed
- `skillforge-langsmith` → For AI/LLM observability

### Step 5: Load Context Protocol
**WHEN agent is activated** → Read `.claude/instructions/orchestration.md` (v2.0 with MCP awareness)
**ALWAYS** record decisions, evidence, and MCP usage to `.claude/context/shared-context.json`

### Examples of Dynamic Discovery
```
User: "Add paginated search with rate limiting"

OLD WAY (keyword matching):
  → Match "API" → backend-system-architect
  → Load 3 full SKILL.md files (~2500 tokens)

NEW WAY (semantic discovery):
  1. agent-registry.json → backend-system-architect (confidence: 0.95)
  2. Check workflows/ → secure-api-endpoint.md exists!
  3. Load composed workflow (~800 tokens)
  4. Use context7 for current FastAPI docs
  Token savings: 68%
```

## 👥 Available Agents

- **ai-ml-engineer**
- **backend-system-architect**
- **code-quality-reviewer**
- **frontend-ui-developer**
- **product-manager**
- **rapid-ui-designer**
- **sprint-prioritizer**
- **studio-coach**
- **ux-researcher**
- **whimsy-injector**


## 🧠 IMPORTANT: Context Protocol

**WHEN working with activated agents, YOU MUST:**

1. **Read** `.claude/instructions/context-middleware.md` before agent work begins
2. **Record** all decisions, architectural choices, and evidence to `.claude/context/shared-context.json`
3. **Check** existing context at session start to maintain continuity across conversations
4. **Share** context between agents when coordinating multi-agent tasks

**Context file location:** `.claude/context/shared-context.json`
**Full protocol details:** Read `.claude/instructions/context.md` for advanced scenarios

## ⚙️ MCP Servers

**Installed (3 core servers):** ~7k tokens
- **memory** - Conversation persistence across sessions
- **sequential-thinking** - Advanced multi-step reasoning
- **context7** - Library documentation lookup

**Optional (add to `.mcp.json` as needed):**
- **browsermcp** - Browser automation
- **shadcn** - UI component integration

📖 **Full guide**: Read `.claude/instructions/mcp-optimization.md` for task-based recommendations, monitoring with `/context`, and advanced optimizations.

## 📚 Claude Code Skills

**18 specialized knowledge modules** installed in `.claude/skills/` directory:

| Skill | Use When |
|-------|----------|
| **ai-native-development** | Building RAG pipelines, embeddings, vector DBs, LLM integration |
| **api-design-framework** | Designing REST/GraphQL/gRPC APIs |
| **architecture-decision-record** | Documenting architectural decisions (ADRs) |
| **code-review-playbook** | Conducting code reviews with conventional comments |
| **database-schema-designer** | Designing SQL/NoSQL schemas and migrations |
| **design-system-starter** | Creating design systems, tokens, components |
| **edge-computing-patterns** | Deploying to Cloudflare Workers, Vercel Edge, Deno Deploy |
| **evidence-verification** | Collecting quality evidence (v3.5.0) |
| **quality-gates** | Complexity assessment and gate validation (v3.5.0) |
| **react-server-components-framework** | Next.js 15 App Router, RSC, Server Actions |
| **security-checklist** | Security audits, OWASP Top 10 compliance |
| **streaming-api-patterns** | SSE, WebSockets, ReadableStream, real-time APIs |
| **testing-strategy-builder** | Building test plans and coverage strategies |
| **type-safety-validation** | End-to-end type safety with Zod, tRPC, Prisma |
| **performance-optimization** | Database queries, bundle size, Core Web Vitals, caching (v3.7.0) |
| **devops-deployment** | CI/CD pipelines, Docker, Kubernetes, GitOps (v3.7.0) |
| **observability-monitoring** | Logging, metrics, tracing, alerting (v3.7.0) |

**How to use skills (v4.0 - Progressive Loading):**
1. **FIRST**: Read `.claude/skills/<skill-name>/capabilities.json` (~100 tokens)
   - Contains searchable capability index with keywords and example problems
   - Shows which specific reference/template files to load
2. **THEN**: Load only the specific file needed from `references/` or `templates/`
3. **AVOID**: Loading full SKILL.md unless you need the complete overview
4. **TOKEN SAVINGS**: 60-80% by using progressive loading

**Example - API Design Task:**
```
OLD: Load .claude/skills/api-design-framework/SKILL.md (600 tokens)
NEW: Load .claude/skills/api-design-framework/capabilities.json (100 tokens)
     → Find "pagination" capability
     → Load only references/pagination.md (150 tokens)
     Savings: 58%
```

## 🏭 Production Features (v3.5.0)

### Evidence-Based Verification
- **Proof over promises**: Exit codes, test results, build logs
- **Quality standards**: Minimum → Production-Grade → Gold Standard
- **Auto-recorded**: All agents record evidence in shared context
- **No hallucinations**: Evidence proves completion, not claims

### Quality Gates
- **Complexity scoring**: 1-5 scale prevents overwhelming tasks
- **Blocking thresholds**: >3 questions, missing deps, 3+ attempts
- **Stuck detection**: Auto-escalate after 3 failed attempts
- **Failure cascades**: Block dependent tasks when upstream fails

### Auto-Scanning
- **Security scans**: npm audit / pip-audit on every review
- **Auto-trigger**: Code Quality Reviewer runs security checks
- **Blocking**: Critical vulnerabilities block approval
- **Fix commands**: Actionable remediation guidance

## 📁 Project Structure (v4.0.0 - Dynamic MCP)

```
.claude/
├── agent-registry.json    # 🆕 Semantic agent/skill discovery (v4.0)
├── agents/                # 10 specialist agent personalities
├── instructions/          # Orchestration & context rules
│   ├── orchestration.md   # 🔄 Updated with MCP integration (v2.0)
│   └── ...                # Core instructions
├── skills/                # 18 specialized knowledge modules
│   └── */capabilities.json # 🆕 Progressive loading indexes (v4.0)
├── workflows/             # 🆕 Pre-composed multi-skill workflows (v4.0)
│   ├── secure-api-endpoint.md
│   ├── full-stack-feature.md
│   └── ai-integration.md
├── schemas/               # 🆕 JSON schemas for validation (v4.0)
│   ├── agent-registry.schema.json
│   └── skill-capabilities.schema.json
├── context/               # Shared context & session data
│   └── shared-context.json
├── commands/              # Squad parallel execution commands
├── examples/              # Squad workflow examples
├── context-triggers.md    # Keyword-based agent activation (legacy)
└── settings.local.json    # MCP server configuration
```

## 🆕 Dynamic MCP Architecture (v4.0)

**Inspired by Docker's Dynamic MCPs blog post**, this system transforms static agent/skill configuration into semantic discovery:

| Pattern | Implementation |
|---------|---------------|
| `mcp-find` | `agent-registry.json` semantic matching |
| `mcp-add` | Progressive skill loading (capabilities.json first) |
| `code-mode` | Composed workflows in `.claude/workflows/` |
| Dynamic selection | Load only needed skill sections |

**Token Savings:** 60-80% on typical tasks through progressive loading and workflow composition.

**MCP Integration:**
- Always use `context7` for current library documentation
- Use `mcp-find` to discover additional development tools
- Record MCP usage in `shared-context.json` for workflow optimization

## 💾 Golden Dataset & Data Protection

**The golden dataset contains 98 curated technical documents** with embeddings for semantic search testing.

### Quick Stats
- **98 Analyses** (completed) | **98 Artifacts** | **415 Chunks**
- Content: 76 articles, 19 tutorials, 3 research papers
- Topics: RAG, LangGraph, Prompt Engineering, API Design, Testing, etc.

### URL Contract (Important)
- Golden fixture documents must include **`source_url`**.
- Golden dataset analyses must store the **real canonical URL** in `analyses.url` (not placeholder `*.skillforge.dev/*` URLs).
- `backup_golden_dataset.py verify` will fail if placeholder golden URLs are present.

### Backup Commands
```bash
cd backend

# Create JSON backup (recommended, version controlled)
poetry run python scripts/backup_golden_dataset.py backup

# Verify backup integrity
poetry run python scripts/backup_golden_dataset.py verify

# Restore from backup (regenerates embeddings)
poetry run python scripts/backup_golden_dataset.py restore --replace
```

### Data Protection Files
| File | Location | Purpose |
|------|----------|---------|
| JSON Backup | `backend/data/golden_dataset_backup.json` | Portable, git-tracked |
| Metadata | `backend/data/golden_dataset_metadata.json` | Quick stats |
| SQL Dump | `backend/data/golden_dataset_dump.sql` | Local only (gitignored) |

### Recovery
```bash
# New dev environment
docker compose up -d postgres
poetry run alembic upgrade head
poetry run python scripts/backup_golden_dataset.py restore
```

---
*💡 This CLAUDE.md uses directive language patterns from Anthropic best practices (2025) to ensure proactive agent activation and context awareness while saving ~80% tokens through on-demand instruction loading.*

*📦 v4.0.0: Dynamic MCP architecture with semantic discovery, progressive loading, and workflow composition.*