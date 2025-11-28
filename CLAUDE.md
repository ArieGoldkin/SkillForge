---
name: claude-main
description: AI Agent Hub - Modular Intelligence System
version: 3.7.1
---

# 🚀 AI Agent Hub - Intelligent Orchestration

**Mode**: ⚡ Squad (Parallel)

## 📦 Project: SkillForge

**Intelligent Learning Integration Platform** - Multi-agent system that analyzes technical content (URLs, videos, repos) via LangGraph pipeline and generates AI-ready implementation guides with Socratic tutoring.

**Stack**: React 19 + FastAPI + LangGraph 0.6.7 + PostgreSQL/PGVector

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


## 📋 Modular Instruction System

This project uses specialized instruction files to optimize tokens while maintaining agent capabilities.

**YOU MUST** follow the agent activation protocol below for every task.

### 📁 Available Instruction Files

| File | Contains |
|------|----------|
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


## ⚡ MANDATORY: Agent Activation Protocol

**BEFORE responding to ANY user task, YOU MUST execute this protocol:**

### Step 1: Check for Agent Triggers
Read `.claude/context-triggers.md` and check if the user's request contains keywords matching any agent.

### Step 2: Activate Matching Agent(s)
**IF keywords match** → Read `.claude/instructions/orchestration.md`, then **MUST READ** `.claude/agents/<agent-name>.md` to load the agent's full capabilities, protocols, and implementation requirements.
**IF multi-domain task** (e.g., "build app", "full project") → Activate Studio Coach, then read `.claude/agents/studio-coach.md`.
**IF no match** → Proceed with general capabilities, but remain alert for implicit domain signals.

### Step 3: Load Context Protocol (When Using Agents)
**WHEN agent is activated** → Read `.claude/instructions/context-middleware.md` for context management rules.
**ALWAYS** record decisions, evidence, and actions to `.claude/context/shared-context.json`.

### Examples of Trigger Matching
- User says "design REST API" → **Backend System Architect** (keywords: API, REST, backend)
  → Read `.claude/agents/backend-system-architect.md` for implementation protocols
- User says "create React component" → **Frontend UI Developer** (keywords: React, component, UI)
  → Read `.claude/agents/frontend-ui-developer.md` for component patterns
- User says "build task manager app" → **Studio Coach** coordinates multiple agents (multi-domain)
  → Read `.claude/agents/studio-coach.md` for orchestration rules

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

**How to use skills:**
- **PROACTIVELY read** `.claude/skills/<skill-name>/SKILL.md` when the user's task matches the skill description
- **Progressive loading** - Start with SKILL.md, then access templates/examples as needed
- **Apply patterns** - Use templates, checklists, and best practices from skill files
- **Examples:** API design → read `.claude/skills/api-design-framework/SKILL.md`; Security review → read `.claude/skills/security-checklist/SKILL.md`

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

## 📁 Project Structure (v3.5.9+)

```
.claude/
├── agents/              # 10 specialist agent personalities
├── instructions/        # Orchestration & context rules
│   ├── ...              # Core instructions
│   └── supervisor-rules.md, squad-roster.md, ... # Squad coordination
├── skills/              # 18 specialized knowledge modules
├── context/             # Shared context & session data
│   └── shared-context.json
├── commands/            # Squad parallel execution commands
├── examples/            # Squad workflow examples
├── context-triggers.md  # Keyword-based agent activation
└── settings.local.json  # MCP server configuration
```

---
*💡 This CLAUDE.md uses directive language patterns from Anthropic best practices (2025) to ensure proactive agent activation and context awareness while saving ~80% tokens through on-demand instruction loading.*

*📦 v3.7.1: All Claude resources unified under `.claude/` following Anthropic's recommended patterns.*