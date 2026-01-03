# Agent Registry & Capabilities

*Load this file when you need to work with specific agents*

## Agent Overview

SkillForge has **20 specialized agents** organized into two categories:

| Category | Count | Purpose |
|----------|-------|---------|
| **Technical Agents** | 14 | Implementation, quality, security |
| **Product Agents** | 6 | Strategy, prioritization, requirements |

---

## Product Thinking Pipeline (NEW)

Sequential pipeline for product decisions before technical implementation:

```
market-intelligence → product-strategist → prioritization-analyst → business-case-builder → requirements-translator → metrics-architect → [TECHNICAL HANDOFF]
```

### market-intelligence 🔮
**Role**: Market research specialist who analyzes competitive landscapes, identifies market trends, sizes opportunities (TAM/SAM/SOM), and surfaces threats/opportunities
**Color**: Violet
**Tools**: Read, Write, WebSearch, WebFetch, Grep, Glob, Bash
**Triggers**: `market research`, `competitor analysis`, `TAM`, `SWOT`, `market trends`
**Output**: Market report with competitors, sizing, SWOT analysis

### product-strategist 🎯
**Role**: Product strategy specialist who validates value propositions, aligns features with business goals, evaluates build/buy/partner decisions
**Color**: Purple
**Tools**: Read, Write, WebSearch, WebFetch, Grep, Glob, Bash
**Triggers**: `product strategy`, `value proposition`, `should we build`, `go/no-go`
**Output**: Strategic go/no-go recommendation with rationale

### prioritization-analyst 📊
**Role**: Prioritization specialist who scores features using RICE/ICE/WSJF frameworks, analyzes opportunity costs, manages backlog ranking
**Color**: Plum
**Tools**: Read, Write, Grep, Glob, Bash
**Triggers**: `prioritization`, `RICE`, `ICE`, `backlog`, `what to build next`
**Output**: RICE-scored backlog with recommended sequence

### business-case-builder 💰
**Role**: Business analyst who builds ROI projections, cost-benefit analyses, risk assessments, and investment justifications
**Color**: Indigo
**Tools**: Read, Write, WebSearch, Grep, Glob, Bash
**Triggers**: `business case`, `ROI`, `cost-benefit`, `investment`, `justification`
**Output**: Business case with ROI, sensitivity analysis, risks

### requirements-translator 📝
**Role**: Requirements specialist who transforms ambiguous ideas into clear PRDs, user stories with acceptance criteria, and scoped specifications
**Color**: Magenta
**Tools**: Read, Write, Grep, Glob, Bash
**Triggers**: `requirements`, `PRD`, `user stories`, `acceptance criteria`, `specification`
**Output**: PRD with user stories, acceptance criteria, scope boundaries

### metrics-architect 📈
**Role**: Metrics specialist who designs OKRs, KPIs, success criteria, and instrumentation plans to measure product outcomes
**Color**: Orchid
**Tools**: Read, Write, Grep, Glob, Bash
**Triggers**: `metrics`, `KPI`, `OKR`, `success criteria`, `instrumentation`
**Output**: Metrics framework with OKRs, KPIs, experiment design

---

## Technical Agents

### Architecture & Design

#### backend-system-architect 🏗️
**Role**: Backend architect who designs REST/GraphQL APIs, database schemas, microservice boundaries, and distributed systems
**Tools**: Read, Edit, MultiEdit, Write, Bash, Grep, Glob
**Triggers**: API design, database schema, microservices, scalability

#### workflow-architect 🔄
**Role**: Multi-agent workflow specialist who designs LangGraph pipelines, implements supervisor-worker patterns, manages state and checkpointing
**Model**: Opus (complex reasoning)
**Tools**: Bash, Read, Write, Edit, Grep, Glob
**Triggers**: LangGraph, workflow, multi-agent, supervisor, RAG pipeline

#### system-design-reviewer 🔍
**Role**: System design reviewer for architectural decisions
**Tools**: Read, Grep, Glob
**Triggers**: Architecture review, system design, scalability review

### Implementation

#### frontend-ui-developer ⚛️
**Role**: Frontend developer who builds React 19/TypeScript components with optimistic updates, concurrent features, Zod-validated APIs
**Tools**: Read, Edit, MultiEdit, Write, Bash, Grep, Glob
**Triggers**: React components, TypeScript, frontend implementation

#### rapid-ui-designer 🎨
**Role**: UI/UX designer specializing in rapid prototyping with Tailwind CSS
**Tools**: Write, Read, Grep, Glob
**Triggers**: UI design, mockups, Tailwind, design system

#### database-engineer 🗄️
**Role**: PostgreSQL specialist who designs schemas, creates migrations, optimizes queries, and configures pgvector/full-text search
**Tools**: Bash, Read, Write, Edit, Grep, Glob
**Triggers**: PostgreSQL, migrations, database optimization, pgvector

#### llm-integrator 🤖
**Role**: LLM integration specialist who connects to OpenAI/Anthropic/Ollama APIs, designs prompt templates, implements function calling
**Tools**: Bash, Read, Write, Edit, Grep, Glob, WebFetch
**Triggers**: LLM API, prompt engineering, function calling, streaming

#### data-pipeline-engineer 📦
**Role**: Data pipeline specialist who generates embeddings, implements chunking strategies, manages vector indexes
**Tools**: Bash, Read, Write, Edit, Grep, Glob
**Triggers**: Embeddings, chunking, vector indexes, data transformation

### Quality & Security

#### code-quality-reviewer ✅
**Role**: Quality assurance expert who reviews code for bugs, security vulnerabilities, performance issues
**Tools**: Read, Bash, Grep, Glob
**Triggers**: Code review, quality check, linting, type checking

#### test-generator 🧪
**Role**: Test specialist who analyzes code coverage gaps, generates unit/integration tests, creates test fixtures
**Tools**: Bash, Read, Write, Edit, Grep, Glob
**Triggers**: Unit tests, integration tests, test coverage, MSW mocking

#### security-auditor 🔒
**Role**: Security specialist who scans for vulnerabilities, audits dependencies, checks OWASP Top 10 compliance
**Tools**: Bash, Read, Grep, Glob
**Triggers**: Security scan, OWASP, vulnerability audit, secrets detection

#### security-layer-auditor 🛡️
**Role**: Security layer auditor for defense-in-depth review
**Tools**: Read, Bash, Grep, Glob
**Triggers**: Security layers, defense in depth, security architecture

#### debug-investigator 🐛
**Role**: Debug specialist who performs systematic root cause analysis on bugs and failures
**Tools**: Bash, Read, Grep, Glob
**Triggers**: Bug investigation, root cause analysis, debugging, error tracing

### Research

#### ux-researcher 👥
**Role**: User research specialist who creates personas, maps user journeys, validates design decisions
**Tools**: Write, Read, WebSearch, Grep, Glob
**Triggers**: User research, personas, user journey, JTBD, usability

---

## Capabilities Matrix

| Agent | Strategy | Design | Backend | Frontend | Data | Quality | Security |
|-------|----------|--------|---------|----------|------|---------|----------|
| market-intelligence | ✅ | - | - | - | - | - | - |
| product-strategist | ✅ | - | - | - | - | - | - |
| prioritization-analyst | ✅ | - | - | - | - | - | - |
| business-case-builder | ✅ | - | - | - | - | - | - |
| requirements-translator | ✅ | - | - | - | - | - | - |
| metrics-architect | ✅ | - | - | - | - | - | - |
| backend-system-architect | - | ✅ | ✅ | - | - | - | - |
| workflow-architect | - | ✅ | ✅ | - | ✅ | - | - |
| frontend-ui-developer | - | - | - | ✅ | - | - | - |
| rapid-ui-designer | - | ✅ | - | ✅ | - | - | - |
| database-engineer | - | - | ✅ | - | ✅ | - | - |
| llm-integrator | - | - | ✅ | - | ✅ | - | - |
| data-pipeline-engineer | - | - | - | - | ✅ | - | - |
| code-quality-reviewer | - | - | - | - | - | ✅ | - |
| test-generator | - | - | - | - | - | ✅ | - |
| security-auditor | - | - | - | - | - | - | ✅ |
| debug-investigator | - | - | ✅ | ✅ | - | ✅ | - |
| ux-researcher | ✅ | ✅ | - | - | - | - | - |

---

## Agent Collaboration Patterns

### Product → Technical Flow
```
1. market-intelligence → Competitive landscape
2. product-strategist → Go/no-go decision
3. prioritization-analyst → RICE-scored backlog
4. business-case-builder → Investment justification
5. requirements-translator → PRD + user stories
6. metrics-architect → Success criteria
7. ux-researcher → User journeys, personas
8. backend-system-architect / frontend-ui-developer → Implementation
9. code-quality-reviewer → Quality gate
10. metrics-architect → Validate outcomes
```

### Technical Implementation Flow
```
1. backend-system-architect → API design
2. database-engineer → Schema + migrations
3. frontend-ui-developer → UI implementation
4. test-generator → Test coverage
5. code-quality-reviewer → Quality review
6. security-auditor → Security scan
```

### AI Feature Flow
```
1. workflow-architect → LangGraph design
2. llm-integrator → LLM integration
3. data-pipeline-engineer → Embeddings/vectors
4. test-generator → AI-specific tests
```

---

## Common Invocation Patterns

### Starting a New Feature
```
"Use market-intelligence to research competitors for [feature]"
"Use product-strategist to evaluate if we should build [feature]"
"Use prioritization-analyst to score [feature] against the backlog"
```

### Implementation
```
"Use backend-system-architect to design the API for [feature]"
"Use frontend-ui-developer to build the [component]"
"Use workflow-architect to design the LangGraph pipeline"
```

### Quality Assurance
```
"Use code-quality-reviewer to review [PR/files]"
"Use security-auditor to scan [directory]"
"Use test-generator to add tests for [module]"
```
