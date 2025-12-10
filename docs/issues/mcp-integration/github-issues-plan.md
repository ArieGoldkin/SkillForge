# MCP Integration - GitHub Issues Plan

> **Version**: 1.0.0
> **Date**: December 2025
> **Status**: Planning
> **Related**: #166 (Dynamic MCP for Claude Code - development tooling)

## Executive Summary

This document outlines the complete GitHub issue structure for MCP (Model Context Protocol) integration into SkillForge. The implementation is split into two phases:

1. **Phase 1: MCP Consumer** - SkillForge agents consume external MCP tools
2. **Phase 2: MCP Provider** - SkillForge exposes its capabilities as an MCP server

---

## Table of Contents

1. [Milestone Structure](#milestone-structure)
2. [New Labels Required](#new-labels-required)
3. [Issues to Modify](#issues-to-modify)
4. [Phase 1 Issues: MCP Consumer](#phase-1-issues-mcp-consumer)
5. [Phase 2 Issues: MCP Provider](#phase-2-issues-mcp-provider)
6. [Documentation Issues](#documentation-issues)
7. [Issue Templates](#issue-templates)
8. [Dependencies Graph](#dependencies-graph)

---

## Milestone Structure

### Option A: Dedicated MCP Sprint (Recommended)

```
Sprint 8  (Current)  → Embeddings & Search (Dec 22)
Sprint 9  (NEW)      → MCP Tool Integration (Jan 5)   ← Phase 1
Sprint 10 (NEW)      → MCP Server & Polish (Jan 19)   ← Phase 2
Sprint 7  (Existing) → Testing & Deployment (Feb 4)   ← Final testing
```

### Option B: Integrate into Sprint 6

Since Sprint 6 is "Content Expansion" with GitHub repo analysis (#78), MCP could naturally fit:

```
Sprint 6 (Modified) → Content Expansion + MCP Foundation
  - YouTube extraction (#77)
  - GitHub extraction via MCP (#78 modified)  ← Use GitHub MCP instead of pygithub
  - MCP Client infrastructure (new issues)
```

### Recommended: Option A

**Rationale**: MCP is a significant architectural addition. Mixing it with Sprint 6 feature work could create scope creep. A dedicated sprint allows focused implementation and testing.

---

## New Labels Required

Create these labels before creating issues:

```bash
# MCP-specific label
gh label create "🔌 mcp" --description "Model Context Protocol integration" --color "6f42c1"

# Sprint label
gh label create "sprint-9" --description "Sprint 9: MCP Integration" --color "1D76DB"
gh label create "sprint-10" --description "Sprint 10: MCP Server" --color "1D76DB"

# Epic label for grouping
gh label create "epic:mcp" --description "MCP Integration Epic" --color "d4a5a5"
```

| Label | Color | Description |
|-------|-------|-------------|
| `🔌 mcp` | `#6f42c1` (purple) | Model Context Protocol integration |
| `sprint-9` | `#1D76DB` (blue) | Sprint 9 tasks |
| `sprint-10` | `#1D76DB` (blue) | Sprint 10 tasks |
| `epic:mcp` | `#d4a5a5` (rose) | MCP Integration Epic |

---

## Issues to Modify

### Issue #166: Dynamic MCP Architecture for Claude Code

**Current State**: Open, no milestone
**Action**: Update to clarify scope and link to new MCP issues

**Modifications**:
1. Add clarifying note distinguishing development-time MCP from production MCP
2. Link to new epic issues
3. Keep as separate track (Claude Code tooling vs production agents)

```markdown
## Update to Add:

### Scope Clarification

This issue focuses on **development-time MCP** - improving Claude Code's ability to help developers by using MCP tools during coding sessions.

For **production MCP integration** (SkillForge agents using MCP tools at runtime), see:
- Epic: #XXX (MCP Integration Epic)
- Phase 1: #XXX-XXX (MCP Consumer)
- Phase 2: #XXX-XXX (MCP Provider)

The two tracks are complementary:
- **#166** = Better developer experience with Claude Code
- **Epic** = Better analysis quality through real-time data
```

---

### Issue #78: GitHub Repository Analysis

**Current State**: Open, Sprint 6, uses `pygithub`
**Action**: Consider MCP alternative or hybrid approach

**Option 1: Keep pygithub, add MCP later**
- Simpler, ships faster
- MCP becomes enhancement in Phase 1

**Option 2: Use GitHub MCP from start** (Recommended if MCP timeline allows)
- Cleaner architecture
- Sets precedent for MCP-first external integrations
- Requires MCP infrastructure to be ready

**Modifications** (if Option 2):
```markdown
## Updated Acceptance Criteria

- [ ] ~~pygithub library integration working~~
- [x] GitHub MCP server integration (via MCPClientPool)
- [ ] GitHub extractor service using MCP tools:
  - `github:get_repo` - Repository metadata
  - `github:get_readme` - README content
  - `github:get_file_tree` - Repository structure
  - `github:get_languages` - Language breakdown
- [ ] Fallback to direct API if MCP unavailable
- [ ] Unit tests with MCP mock server

## Dependencies
- NEW: MCP Client Infrastructure (#XXX)
- Task 1.4.2 (Jina Reader Service - extraction pattern)
```

---

## Phase 1 Issues: MCP Consumer

### Epic Issue

```markdown
# [Epic] MCP Integration - External Tool Consumption

## Summary

Enable SkillForge analysis agents to consume external MCP tools for grounded,
real-time analysis. This transforms agents from purely LLM-reasoning to
tool-augmented reasoning with access to live data.

## Background

Currently, agents like `security_auditor` and `dependency_mapper` rely solely
on LLM knowledge, which can be outdated. MCP integration allows these agents
to query real-time data:

- CVE databases for current vulnerabilities
- npm/PyPI registries for package versions
- GitHub for repository metadata and security advisories

## Scope

### In Scope
- MCP client infrastructure (connection pooling, health checks)
- Tool registry with agent-capability mapping
- Tool-enabled agent factory
- Integration with security_auditor and dependency_mapper
- Graceful degradation when MCP servers unavailable
- Observability and metrics

### Out of Scope (Phase 2)
- Exposing SkillForge as MCP server
- MCP Resources and Prompts primitives
- MCP Subscriptions for real-time updates

## Success Metrics

- [ ] security_auditor can query CVE database in real-time
- [ ] dependency_mapper can fetch current package versions
- [ ] Agents work correctly when MCP servers are unavailable
- [ ] Tool calls are traced in LangSmith
- [ ] <500ms added latency per tool call

## Child Issues

- [ ] #XXX MCP Client Pool & Connection Management
- [ ] #XXX Tool Registry & Capability Mapping
- [ ] #XXX Tool-Enabled Agent Factory
- [ ] #XXX Security Auditor MCP Integration
- [ ] #XXX Dependency Mapper MCP Integration
- [ ] #XXX MCP Error Handling & Resilience
- [ ] #XXX MCP Integration Tests

## References

- [MCP Specification](https://modelcontextprotocol.io/)
- [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters)
- Design doc: `docs/architecture/mcp-tool-service-design.md`
```

**Labels**: `epic:mcp`, `🔌 mcp`, `🔵 backend`, `✨ feature`, `⚡ high`
**Milestone**: Sprint 9: MCP Integration

---

### Issue 1: MCP Client Pool & Connection Management

```markdown
# [🔵 Backend][🔌 MCP] MCP Client Pool & Connection Management [5 pts]

## Summary

Implement `MCPClientPool` for managing connections to external MCP servers with
connection pooling, health checks, and graceful degradation.

## Background

MCP servers can use different transports:
- **stdio**: Local subprocess (spawns child process)
- **HTTP/SSE**: Remote server (network calls)

We need a connection pool that:
- Lazily initializes connections (don't spawn processes at startup)
- Reuses connections across requests
- Monitors health and reconnects on failure
- Supports multiple concurrent MCP servers

## Acceptance Criteria

- [ ] `MCPClientPool` class implemented in `backend/app/services/mcp/client.py`
- [ ] Support for both stdio and HTTP transports
- [ ] Lazy connection initialization (connect on first tool use)
- [ ] Connection health monitoring with automatic recovery
- [ ] Configurable timeouts and retry policies
- [ ] Graceful shutdown (cleanup child processes)
- [ ] Logging with structlog for all connection events
- [ ] Unit tests with >80% coverage

## Technical Details

### Key Classes

```python
class MCPClientPool:
    """Connection pool for MCP servers."""

    async def get_tools(self, server_name: str) -> AsyncIterator[list[BaseTool]]:
        """Context manager yielding tools from a server."""

    async def get_tools_for_capabilities(
        self, capabilities: list[str]
    ) -> list[BaseTool]:
        """Get tools matching capability IDs like 'github:get_repo'."""

    async def health_check(self) -> dict[str, bool]:
        """Check health of all configured servers."""
```

### Configuration

```python
@dataclass
class MCPServerConfig:
    name: str
    transport: MCPTransport  # STDIO | HTTP | SSE
    command: str | None      # For stdio
    url: str | None          # For HTTP/SSE
    timeout: float = 30.0
    max_retries: int = 3
```

## Files to Create

- `backend/app/services/mcp/__init__.py`
- `backend/app/services/mcp/client.py`
- `backend/app/services/mcp/config.py`
- `backend/tests/unit/services/mcp/test_client.py`

## Dependencies

- `langchain-mcp-adapters>=0.2.1`
- `mcp>=1.0.0`

## References

- [langchain-mcp-adapters MultiServerMCPClient](https://github.com/langchain-ai/langchain-mcp-adapters)
- Design doc: `docs/architecture/mcp-tool-service-design.md`
```

**Labels**: `🔵 backend`, `🔌 mcp`, `✨ feature`, `⚡ high`, `sprint-9`
**Milestone**: Sprint 9: MCP Integration
**Story Points**: 5

---

### Issue 2: Tool Registry & Capability Mapping

```markdown
# [🔵 Backend][🔌 MCP] Tool Registry & Agent Capability Mapping [3 pts]

## Summary

Implement `ToolRegistry` for managing which MCP tools each agent can access,
preventing tool overload and ensuring agents only see relevant capabilities.

## Background

Anthropic recommends limiting agents to 2-5 tools for optimal accuracy.
Each SkillForge agent has different needs:

| Agent | Tools Needed |
|-------|--------------|
| security_auditor | CVE search, GitHub security advisories |
| dependency_mapper | npm/PyPI package info, GitHub deps |
| tech_comparator | npm stats, GitHub repo stats |
| implementation_planner | None (LLM reasoning sufficient) |

## Acceptance Criteria

- [ ] `ToolRegistry` class in `backend/app/services/mcp/registry.py`
- [ ] Agent-to-capability mapping configuration
- [ ] `is_tool_enabled(agent_type)` check
- [ ] `get_capabilities(agent_type)` returns capability list
- [ ] `filter_tools(tools, agent_type)` filters tool list
- [ ] Configuration via YAML or Python dict
- [ ] Unit tests for all registry operations

## Technical Details

### Capability Format

```
server:tool_name
Examples:
- github:get_repo
- npm:get_package
- cve:search_cves
```

### Agent Configuration

```python
AGENT_TOOL_CONFIGS = {
    "security_auditor": AgentToolConfig(
        enabled=True,
        capabilities=[
            "cve:search_cves",
            "cve:get_cve_details",
            "github:get_security_advisories",
        ],
        max_tool_calls=10,
        tool_timeout=15.0,
    ),
    "dependency_mapper": AgentToolConfig(
        enabled=True,
        capabilities=[
            "npm:get_package",
            "npm:get_versions",
            "pypi:get_package",
        ],
        max_tool_calls=15,
    ),
    # Agents without tools
    "implementation_planner": AgentToolConfig(enabled=False),
    "trend_validator": AgentToolConfig(enabled=False),
}
```

## Files to Create

- `backend/app/services/mcp/registry.py`
- `backend/tests/unit/services/mcp/test_registry.py`

## Dependencies

- Issue #XXX (MCP Client Pool)

## References

- Anthropic tool use best practices
- Design doc: `docs/architecture/mcp-tool-service-design.md`
```

**Labels**: `🔵 backend`, `🔌 mcp`, `✨ feature`, `🔄 medium`, `sprint-9`
**Milestone**: Sprint 9: MCP Integration
**Story Points**: 3

---

### Issue 3: Tool-Enabled Agent Factory

```markdown
# [🔵 Backend][🤖 LangGraph][🔌 MCP] Tool-Enabled Agent Factory [5 pts]

## Summary

Create `create_tool_enabled_agent()` factory function that creates agents
capable of calling MCP tools during reasoning, while maintaining structured
output via ToolStrategy.

## Background

Current agents use `create_structured_agent()` which produces structured
output but cannot call external tools. We need a new factory that:

1. Binds MCP tools to the agent
2. Allows tool calling during reasoning
3. Still produces structured output (Pydantic model)
4. Enhances system prompt with tool usage guidelines

## Acceptance Criteria

- [ ] `create_tool_enabled_agent()` in `backend/app/workflows/agents/base.py`
- [ ] Accepts `mcp_tools: list[BaseTool]` parameter
- [ ] Configurable `max_tool_calls` limit
- [ ] System prompt enhancement with tool guidance
- [ ] Parallel tool calls enabled for efficiency
- [ ] Works with existing `run_agent_with_tracking()`
- [ ] Tool calls traced in LangSmith
- [ ] Unit tests comparing tool-enabled vs structured-only

## Technical Details

### Function Signature

```python
def create_tool_enabled_agent(
    system_prompt: str,
    response_schema: type[BaseModel],
    mcp_tools: Sequence[BaseTool],
    max_tool_calls: int = 5,
) -> Runnable:
    """Create agent that can call MCP tools during reasoning.

    Unlike create_structured_agent which uses ToolStrategy for
    output-only, this agent can invoke external tools during
    reasoning then produce structured response.
    """
```

### Prompt Enhancement

```python
def _enhance_prompt_for_tools(base_prompt: str, tools: list[BaseTool]) -> str:
    """Add tool usage guidelines to system prompt."""
    return f"""
{base_prompt}

## Available Tools
{_format_tool_descriptions(tools)}

## Tool Usage Guidelines
1. Use tools to verify claims about versions, CVEs, packages
2. Don't over-use - trust your knowledge for concepts
3. Handle failures gracefully - note gaps, don't retry
4. Cite tool results in your findings
"""
```

## Files to Modify

- `backend/app/workflows/agents/base.py` - Add new factory

## Files to Create

- `backend/tests/unit/workflows/agents/test_tool_enabled_agent.py`

## Dependencies

- Issue #XXX (MCP Client Pool)
- Issue #XXX (Tool Registry)

## References

- LangChain `create_agent()` with tools
- Existing `create_structured_agent()` implementation
```

**Labels**: `🔵 backend`, `🤖 langgraph`, `🔌 mcp`, `✨ feature`, `⚡ high`, `sprint-9`
**Milestone**: Sprint 9: MCP Integration
**Story Points**: 5

---

### Issue 4: Security Auditor MCP Integration

```markdown
# [🔵 Backend][🤖 LangGraph][🔌 MCP] Security Auditor MCP Integration [3 pts]

## Summary

Integrate MCP tools into the `security_auditor` agent, enabling real-time
CVE lookups and GitHub security advisory checks.

## Background

Currently `security_auditor` identifies vulnerabilities based on LLM
knowledge, which may be outdated. With MCP tools, it can:

- Query CVE database for current vulnerability data
- Check GitHub security advisories for mentioned packages
- Verify CVSS scores are accurate
- Find related CVEs for identified issues

## Acceptance Criteria

- [ ] Update `run_security_auditor()` to accept MCP pool
- [ ] Load tools based on registry capabilities
- [ ] Use `create_tool_enabled_agent()` when tools available
- [ ] Graceful fallback to structured-only when tools unavailable
- [ ] Updated prompt encouraging tool use for verification
- [ ] Tool calls visible in LangSmith traces
- [ ] Integration test with mock CVE MCP server

## Technical Details

### Tool Capabilities

```python
"security_auditor": AgentToolConfig(
    capabilities=[
        "cve:search_cves",        # Search by keyword/package
        "cve:get_cve_details",    # Get specific CVE info
        "github:get_security_advisories",  # Repo advisories
        "github:get_dependabot_alerts",    # Dependabot data
    ],
    max_tool_calls=10,
    tool_timeout=15.0,
)
```

### Updated Function Signature

```python
async def run_security_auditor(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    *,
    mcp_pool: MCPClientPool | None = None,  # NEW
    tool_registry: ToolRegistry | None = None,  # NEW
) -> dict[str, object]:
```

### Example Tool Usage

When agent sees "log4j" in content:
1. Agent calls `cve:search_cves(query="log4j")`
2. Gets back CVE-2021-44228 details with CVSS 10.0
3. Includes accurate CVE reference in findings

## Files to Modify

- `backend/app/workflows/agents/security_auditor.py`

## Files to Create

- `backend/tests/integration/agents/test_security_auditor_mcp.py`

## Dependencies

- Issue #XXX (Tool-Enabled Agent Factory)
- Issue #XXX (Tool Registry)
```

**Labels**: `🔵 backend`, `🤖 langgraph`, `🔌 mcp`, `✨ feature`, `🔄 medium`, `sprint-9`
**Milestone**: Sprint 9: MCP Integration
**Story Points**: 3

---

### Issue 5: Dependency Mapper MCP Integration

```markdown
# [🔵 Backend][🤖 LangGraph][🔌 MCP] Dependency Mapper MCP Integration [3 pts]

## Summary

Integrate MCP tools into the `dependency_mapper` agent for real-time
package version lookups and dependency analysis.

## Background

The dependency mapper identifies packages mentioned in content but
currently cannot verify:

- Current vs mentioned versions
- Deprecation status
- Known vulnerabilities in dependencies
- Accurate download statistics

## Acceptance Criteria

- [ ] Update `run_dependency_mapper()` to accept MCP pool
- [ ] Load npm/PyPI tools based on content type
- [ ] Version comparison (mentioned vs current)
- [ ] Deprecation/security status checks
- [ ] Graceful fallback without tools
- [ ] Integration test with mock npm MCP server

## Technical Details

### Tool Capabilities

```python
"dependency_mapper": AgentToolConfig(
    capabilities=[
        "npm:get_package",        # Package metadata
        "npm:get_versions",       # Version history
        "npm:get_dependencies",   # Dependency tree
        "pypi:get_package",       # PyPI package info
        "pypi:get_versions",      # PyPI versions
        "github:get_repo_dependencies",  # package.json/requirements.txt
    ],
    max_tool_calls=15,  # May need many lookups
)
```

### Example Enhancement

Before (LLM only):
```
"react": mentioned in content, likely recent version
```

After (with MCP):
```
"react": version 18.2.0 mentioned, current is 19.1.0 (Dec 2024)
         - 2 major versions behind
         - React 18 still supported until Dec 2025
```

## Files to Modify

- `backend/app/workflows/agents/dependency_mapper.py`

## Files to Create

- `backend/tests/integration/agents/test_dependency_mapper_mcp.py`

## Dependencies

- Issue #XXX (Tool-Enabled Agent Factory)
- Issue #XXX (Tool Registry)
```

**Labels**: `🔵 backend`, `🤖 langgraph`, `🔌 mcp`, `✨ feature`, `🔄 medium`, `sprint-9`
**Milestone**: Sprint 9: MCP Integration
**Story Points**: 3

---

### Issue 6: MCP Error Handling & Resilience

```markdown
# [🔵 Backend][🔌 MCP] MCP Error Handling & Graceful Degradation [3 pts]

## Summary

Implement comprehensive error handling for MCP tool failures, ensuring
agents continue to function when external services are unavailable.

## Background

MCP tool calls can fail due to:
- Network issues (timeout, connection refused)
- Rate limiting (429 responses)
- Server errors (500, maintenance)
- Invalid responses (schema mismatch)

Agents must handle all failures gracefully without crashing the analysis.

## Acceptance Criteria

- [ ] `MCPToolExecutor` wrapper with retry logic
- [ ] Exponential backoff for transient failures
- [ ] Rate limit handling (respect Retry-After)
- [ ] Timeout configuration per tool
- [ ] Circuit breaker for repeated failures
- [ ] Graceful degradation to tool-free mode
- [ ] Error metrics collection
- [ ] All error scenarios logged with structlog

## Technical Details

### Error Handling Strategy

```
┌─────────────────────────────────────────────────────────┐
│                 MCP Tool Call                           │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
    ┌─────────┐            ┌─────────┐
    │ Success │            │ Failure │
    └────┬────┘            └────┬────┘
         │                      │
         ▼               ┌──────┴──────┐
    Return result        ▼             ▼
                   Retryable?     Not Retryable
                        │              │
                   ┌────┴────┐         │
                   ▼         ▼         ▼
              Retry 1    Retry 2   Log & Skip
              (1s)       (2s)      (agent continues)
```

### Circuit Breaker

```python
class MCPCircuitBreaker:
    """Prevents repeated calls to failing servers."""

    def __init__(self, failure_threshold: int = 3, reset_timeout: float = 60):
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED | OPEN | HALF_OPEN

    def record_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def can_execute(self) -> bool:
        return self.state != "OPEN"
```

## Files to Create

- `backend/app/services/mcp/executor.py`
- `backend/app/services/mcp/circuit_breaker.py`
- `backend/tests/unit/services/mcp/test_executor.py`
- `backend/tests/unit/services/mcp/test_circuit_breaker.py`

## Dependencies

- Issue #XXX (MCP Client Pool)
```

**Labels**: `🔵 backend`, `🔌 mcp`, `✨ feature`, `🔄 medium`, `sprint-9`
**Milestone**: Sprint 9: MCP Integration
**Story Points**: 3

---

### Issue 7: MCP Integration Tests

```markdown
# [🔵 Backend][🔌 MCP] MCP Integration Tests with Mock Servers [3 pts]

## Summary

Create comprehensive integration tests for MCP functionality using
mock MCP servers that simulate real external services.

## Background

Unit tests cover individual components, but we need integration tests that:
- Test full tool call flow (agent → pool → server → response)
- Verify graceful degradation scenarios
- Test concurrent tool calls
- Validate LangSmith tracing

## Acceptance Criteria

- [ ] Mock MCP server for testing (FastMCP-based)
- [ ] Integration tests for security_auditor with tools
- [ ] Integration tests for dependency_mapper with tools
- [ ] Tests for connection failure scenarios
- [ ] Tests for tool timeout scenarios
- [ ] Tests for rate limiting scenarios
- [ ] CI pipeline integration
- [ ] Test fixtures for common responses

## Technical Details

### Mock MCP Server

```python
# tests/fixtures/mock_mcp_server.py
from mcp.server.fastmcp import FastMCP

mock_cve = FastMCP("MockCVE")

@mock_cve.tool()
def search_cves(query: str) -> list[dict]:
    """Mock CVE search."""
    return [
        {"id": "CVE-2021-44228", "cvss": 10.0, "description": "Log4j RCE"}
    ] if "log4j" in query.lower() else []

@mock_cve.tool()
def get_cve_details(cve_id: str) -> dict:
    """Mock CVE details."""
    return {"id": cve_id, "cvss": 10.0, "severity": "CRITICAL"}
```

### Test Structure

```
tests/
├── fixtures/
│   ├── mock_mcp_server.py
│   └── mcp_responses/
│       ├── cve_search.json
│       ├── npm_package.json
│       └── github_advisories.json
├── integration/
│   └── mcp/
│       ├── test_security_auditor_mcp.py
│       ├── test_dependency_mapper_mcp.py
│       └── test_error_scenarios.py
```

## Files to Create

- `backend/tests/fixtures/mock_mcp_server.py`
- `backend/tests/fixtures/mcp_responses/*.json`
- `backend/tests/integration/mcp/test_security_auditor_mcp.py`
- `backend/tests/integration/mcp/test_dependency_mapper_mcp.py`
- `backend/tests/integration/mcp/test_error_scenarios.py`

## Dependencies

- All Phase 1 implementation issues
```

**Labels**: `🔵 backend`, `🔌 mcp`, `testing`, `🔄 medium`, `sprint-9`
**Milestone**: Sprint 9: MCP Integration
**Story Points**: 3

---

## Phase 2 Issues: MCP Provider

### Issue 8: SkillForge MCP Server Scaffold

```markdown
# [🔵 Backend][🔌 MCP] SkillForge MCP Server Scaffold [5 pts]

## Summary

Create the foundation for exposing SkillForge capabilities as an MCP server,
allowing external AI systems (Claude Desktop, other agents) to use SkillForge
as a tool.

## Background

MCP is bidirectional - we can both consume and provide. As a provider,
SkillForge can expose:

- **Tools**: `analyze_url()`, `search_chunks()`, `ask_tutor()`
- **Resources**: Analysis results, chunks, embeddings
- **Prompts**: Agent prompt templates

This makes SkillForge composable with other AI systems.

## Acceptance Criteria

- [ ] FastMCP server implementation
- [ ] HTTP transport for remote access
- [ ] Authentication via API key
- [ ] Server capability declaration
- [ ] Health check endpoint
- [ ] Basic `analyze_url` tool exposed
- [ ] OpenAPI-compatible schema generation
- [ ] Integration with existing FastAPI app

## Technical Details

### Server Structure

```python
# backend/app/mcp_server/server.py
from mcp.server.fastmcp import FastMCP

skillforge_mcp = FastMCP(
    "SkillForge",
    description="AI-powered content analysis and learning platform"
)

@skillforge_mcp.tool()
async def analyze_url(url: str, skill_level: str = "intermediate") -> dict:
    """Analyze a URL and generate an implementation guide.

    Args:
        url: URL to analyze (article, video, or repo)
        skill_level: Target skill level (beginner, intermediate, advanced)

    Returns:
        Analysis results with agent findings and artifact
    """
    # Delegate to existing analysis workflow
    ...
```

### Integration Options

1. **Separate process**: Run MCP server alongside FastAPI
2. **Mount in FastAPI**: Use ASGI mounting (recommended)

```python
# Option 2: Mount in FastAPI
from mcp.server.fastmcp import FastMCP
from starlette.routing import Mount

app = FastAPI()
app.mount("/mcp", skillforge_mcp.get_asgi_app())
```

## Files to Create

- `backend/app/mcp_server/__init__.py`
- `backend/app/mcp_server/server.py`
- `backend/app/mcp_server/tools.py`
- `backend/app/mcp_server/auth.py`

## Dependencies

- Phase 1 complete (for understanding MCP patterns)
```

**Labels**: `🔵 backend`, `🔌 mcp`, `✨ feature`, `⚡ high`, `sprint-10`
**Milestone**: Sprint 10: MCP Server
**Story Points**: 5

---

### Issue 9: Expose Analysis Tools via MCP

```markdown
# [🔵 Backend][🔌 MCP] Expose Analysis Tools via MCP [3 pts]

## Summary

Expose SkillForge's core analysis capabilities as MCP tools that external
AI systems can invoke.

## Acceptance Criteria

- [ ] `analyze_url` tool - Full content analysis
- [ ] `search_chunks` tool - Semantic search over stored content
- [ ] `get_analysis` tool - Retrieve existing analysis by ID
- [ ] `list_analyses` tool - List user's analyses
- [ ] Input validation with JSON Schema
- [ ] Structured output with `outputSchema`
- [ ] Rate limiting per API key
- [ ] Usage tracking and metrics

## Tools to Expose

```python
@skillforge_mcp.tool()
async def analyze_url(
    url: str,
    skill_level: str = "intermediate",
    agents: list[str] | None = None,
) -> AnalysisResult:
    """Analyze technical content and generate implementation guide."""

@skillforge_mcp.tool()
async def search_chunks(
    query: str,
    analysis_id: str | None = None,
    limit: int = 10,
) -> list[ChunkResult]:
    """Semantic search over analyzed content."""

@skillforge_mcp.tool()
async def get_implementation_guide(
    analysis_id: str,
    section: str | None = None,
) -> str:
    """Get generated implementation guide (markdown)."""
```

## Files to Modify

- `backend/app/mcp_server/tools.py`

## Dependencies

- Issue #XXX (MCP Server Scaffold)
```

**Labels**: `🔵 backend`, `🔌 mcp`, `✨ feature`, `🔄 medium`, `sprint-10`
**Milestone**: Sprint 10: MCP Server
**Story Points**: 3

---

### Issue 10: Expose Resources via MCP

```markdown
# [🔵 Backend][🔌 MCP] Expose Chunk Resources via MCP [3 pts]

## Summary

Expose SkillForge's analyzed content as MCP Resources, allowing external
systems to read analysis data without invoking tools.

## Background

MCP Resources are read-only data that can be:
- Listed (`resources/list`)
- Read (`resources/read`)
- Subscribed to (`resources/subscribe`)

This is ideal for exposing analysis results, chunks, and embeddings.

## Acceptance Criteria

- [ ] Resource URI scheme: `skillforge://`
- [ ] `skillforge://analysis/{id}` - Full analysis
- [ ] `skillforge://analysis/{id}/chunks` - Chunk list
- [ ] `skillforge://analysis/{id}/artifact` - Generated guide
- [ ] Resource listing with pagination
- [ ] Subscription support for analysis updates
- [ ] MIME types for all resources

## Resource Schema

```python
SKILLFORGE_RESOURCES = [
    {
        "uri": "skillforge://analysis/{analysis_id}",
        "name": "Analysis Result",
        "description": "Complete analysis with all agent findings",
        "mimeType": "application/json",
    },
    {
        "uri": "skillforge://analysis/{analysis_id}/chunks",
        "name": "Content Chunks",
        "description": "Chunked content with embeddings",
        "mimeType": "application/json",
    },
    {
        "uri": "skillforge://analysis/{analysis_id}/artifact",
        "name": "Implementation Guide",
        "description": "Generated markdown guide",
        "mimeType": "text/markdown",
    },
]
```

## Files to Create

- `backend/app/mcp_server/resources.py`

## Dependencies

- Issue #XXX (MCP Server Scaffold)
```

**Labels**: `🔵 backend`, `🔌 mcp`, `✨ feature`, `🔄 medium`, `sprint-10`
**Milestone**: Sprint 10: MCP Server
**Story Points**: 3

---

### Issue 11: Expose Agent Prompts via MCP

```markdown
# [🔵 Backend][🔌 MCP] Expose Agent Prompts via MCP [2 pts]

## Summary

Expose SkillForge's agent prompts as MCP Prompts, allowing external
systems to use our specialized prompts for their own analysis.

## Background

MCP Prompts are reusable templates that can be customized with arguments.
Our agent prompts (security_auditor, dependency_mapper, etc.) are valuable
and could be used by other AI systems.

## Acceptance Criteria

- [ ] `security_audit` prompt with customization args
- [ ] `implementation_plan` prompt
- [ ] `code_review` prompt
- [ ] Arguments for skill_level, framework, focus_areas
- [ ] Prompt listing via `prompts/list`
- [ ] Prompt retrieval via `prompts/get`

## Prompts to Expose

```python
SKILLFORGE_PROMPTS = [
    {
        "name": "security_audit",
        "description": "Comprehensive security analysis prompt",
        "arguments": [
            {"name": "content", "description": "Content to audit", "required": True},
            {"name": "framework", "description": "Target framework (FastAPI, Django, etc.)"},
            {"name": "compliance", "description": "Compliance frameworks (OWASP, GDPR, etc.)"},
        ],
    },
    {
        "name": "implementation_plan",
        "description": "Create step-by-step implementation guide",
        "arguments": [
            {"name": "technology", "required": True},
            {"name": "skill_level", "description": "beginner/intermediate/advanced"},
            {"name": "time_constraint", "description": "Available time for implementation"},
        ],
    },
]
```

## Files to Create

- `backend/app/mcp_server/prompts.py`

## Dependencies

- Issue #XXX (MCP Server Scaffold)
```

**Labels**: `🔵 backend`, `🔌 mcp`, `✨ feature`, `📋 low`, `sprint-10`
**Milestone**: Sprint 10: MCP Server
**Story Points**: 2

---

## Documentation Issues

### Issue 12: MCP Integration Documentation

```markdown
# [📝 Docs][🔌 MCP] MCP Integration Documentation [2 pts]

## Summary

Create comprehensive documentation for MCP integration, covering both
consuming external tools and exposing SkillForge as an MCP server.

## Acceptance Criteria

- [ ] Architecture overview in `docs/architecture/mcp-integration.md`
- [ ] Developer guide: Adding new MCP tools
- [ ] Developer guide: Adding new agent tool capabilities
- [ ] API reference for SkillForge MCP server
- [ ] Troubleshooting guide for MCP issues
- [ ] Configuration reference (environment variables)
- [ ] Update ARCHITECTURE.md with MCP section

## Documentation Structure

```
docs/
├── architecture/
│   ├── mcp-tool-service-design.md (exists)
│   └── mcp-integration.md (overview)
├── guides/
│   ├── mcp-adding-tools.md
│   ├── mcp-agent-capabilities.md
│   └── mcp-server-api.md
└── reference/
    └── mcp-configuration.md
```

## Files to Create/Update

- `docs/architecture/mcp-integration.md`
- `docs/guides/mcp-adding-tools.md`
- `docs/guides/mcp-agent-capabilities.md`
- `docs/ARCHITECTURE.md` (update)

## Dependencies

- All implementation issues complete
```

**Labels**: `📝 documentation`, `🔌 mcp`, `🔄 medium`, `sprint-10`
**Milestone**: Sprint 10: MCP Server
**Story Points**: 2

---

## Dependencies Graph

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         MCP Integration Dependencies                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  PHASE 1: MCP Consumer                                                          │
│                                                                                  │
│  ┌──────────────────┐                                                           │
│  │ #1 MCP Client    │                                                           │
│  │    Pool          │◄────────────────────────────────┐                         │
│  └────────┬─────────┘                                 │                         │
│           │                                           │                         │
│           ▼                                           │                         │
│  ┌──────────────────┐    ┌──────────────────┐        │                         │
│  │ #2 Tool Registry │    │ #6 Error         │        │                         │
│  │                  │    │    Handling      │────────┤                         │
│  └────────┬─────────┘    └──────────────────┘        │                         │
│           │                                           │                         │
│           ▼                                           │                         │
│  ┌──────────────────┐                                │                         │
│  │ #3 Tool-Enabled  │◄───────────────────────────────┘                         │
│  │    Agent Factory │                                                           │
│  └────────┬─────────┘                                                           │
│           │                                                                      │
│      ┌────┴────┐                                                                │
│      ▼         ▼                                                                │
│  ┌────────┐ ┌────────┐                                                          │
│  │ #4 Sec │ │ #5 Dep │                                                          │
│  │ Auditor│ │ Mapper │                                                          │
│  └────┬───┘ └───┬────┘                                                          │
│       │         │                                                               │
│       └────┬────┘                                                               │
│            ▼                                                                    │
│  ┌──────────────────┐                                                           │
│  │ #7 Integration   │                                                           │
│  │    Tests         │                                                           │
│  └──────────────────┘                                                           │
│                                                                                  │
│  ════════════════════════════════════════════════════════════════════════════   │
│                                                                                  │
│  PHASE 2: MCP Provider                                                          │
│                                                                                  │
│  ┌──────────────────┐                                                           │
│  │ #8 MCP Server    │◄──── (Phase 1 Complete)                                   │
│  │    Scaffold      │                                                           │
│  └────────┬─────────┘                                                           │
│           │                                                                      │
│      ┌────┼────────────┐                                                        │
│      ▼    ▼            ▼                                                        │
│  ┌──────┐ ┌──────┐ ┌──────┐                                                     │
│  │ #9   │ │ #10  │ │ #11  │                                                     │
│  │Tools │ │Rsrcs │ │Prompts│                                                    │
│  └──┬───┘ └──┬───┘ └──┬───┘                                                     │
│     │        │        │                                                         │
│     └────────┼────────┘                                                         │
│              ▼                                                                   │
│     ┌──────────────────┐                                                        │
│     │ #12 Documentation│                                                        │
│     └──────────────────┘                                                        │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Summary: Issues to Create

### New Milestones

| Milestone | Title | Description | Due Date |
|-----------|-------|-------------|----------|
| 9 | Sprint 9: MCP Integration | MCP tool consumption for grounded agent analysis | Jan 5, 2026 |
| 10 | Sprint 10: MCP Server | Expose SkillForge as MCP server | Jan 19, 2026 |

### New Labels

| Label | Color | Description |
|-------|-------|-------------|
| `🔌 mcp` | `#6f42c1` | Model Context Protocol integration |
| `sprint-9` | `#1D76DB` | Sprint 9 tasks |
| `sprint-10` | `#1D76DB` | Sprint 10 tasks |
| `epic:mcp` | `#d4a5a5` | MCP Integration Epic |

### Phase 1 Issues (Sprint 9) - 25 points

| # | Title | Points | Priority |
|---|-------|--------|----------|
| E | [Epic] MCP Integration - External Tool Consumption | - | Epic |
| 1 | MCP Client Pool & Connection Management | 5 | High |
| 2 | Tool Registry & Capability Mapping | 3 | Medium |
| 3 | Tool-Enabled Agent Factory | 5 | High |
| 4 | Security Auditor MCP Integration | 3 | Medium |
| 5 | Dependency Mapper MCP Integration | 3 | Medium |
| 6 | MCP Error Handling & Resilience | 3 | Medium |
| 7 | MCP Integration Tests | 3 | Medium |

### Phase 2 Issues (Sprint 10) - 15 points

| # | Title | Points | Priority |
|---|-------|--------|----------|
| 8 | SkillForge MCP Server Scaffold | 5 | High |
| 9 | Expose Analysis Tools via MCP | 3 | Medium |
| 10 | Expose Resources via MCP | 3 | Medium |
| 11 | Expose Agent Prompts via MCP | 2 | Low |
| 12 | MCP Integration Documentation | 2 | Medium |

### Issues to Modify

| # | Title | Modification |
|---|-------|--------------|
| 166 | Dynamic MCP Architecture | Add scope clarification, link to epic |
| 78 | GitHub Repository Analysis | Consider MCP alternative to pygithub |

---

## Next Steps

1. **Create labels** (run `gh label create` commands)
2. **Create milestones** (Sprint 9, Sprint 10)
3. **Create epic issue** first
4. **Create Phase 1 issues** with dependencies
5. **Create Phase 2 issues**
6. **Update issue #166** with clarification
7. **Decide on #78** approach (pygithub vs MCP)
