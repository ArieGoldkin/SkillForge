# Issue #245: Agent Memory Access (RAG)

## Overview

Implement **Reactive and Proactive Recall** patterns from Google ADK's Context Engineering framework. This enables agents to search past analyses, vulnerability patterns, and learned knowledge instead of working in isolation.

**Sprint:** 11 - Context Engineering
**Story Points:** 5
**Dependencies:** Issue #244 (Handle Pattern) - Completed

## Problem Statement

Currently, agents work in complete isolation with no access to:
- Similar past security analyses
- Previously identified vulnerability patterns
- User's historical findings
- Best practices learned from past analyses

## Solution: Dual Recall Patterns

### 1. Reactive Recall (Agent-initiated)
Agent recognizes knowledge gap and explicitly searches using MCP tool:

```
┌─────────────────────────────────────────────────────────────────┐
│  Agent: "I need to check for similar vulnerability patterns"    │
│     │                                                           │
│     └─> Calls: search_memory(query="SQL injection", type="patterns")
│                     │                                           │
│                     └─> Returns: [3 similar findings from past] │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Proactive Recall (Pre-injection)
System automatically injects relevant context before agent invocation:

```
┌─────────────────────────────────────────────────────────────────┐
│  Before Agent Execution:                                        │
│     │                                                           │
│     ├─> System searches memory based on content_summary         │
│     │                                                           │
│     └─> Injects relevant_past_findings into agent context      │
└─────────────────────────────────────────────────────────────────┘
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AGENT MEMORY SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  STORAGE LAYER                     RETRIEVAL LAYER              │
│  ═════════════                     ═══════════════              │
│                                                                  │
│  ┌──────────────┐                  ┌──────────────────┐         │
│  │ AgentMemory  │                  │ AgentMemoryService│         │
│  │   Model      │◄────────────────►│                  │         │
│  │              │                  │ - store()        │         │
│  │ - id         │                  │ - search()       │         │
│  │ - analysis_id│                  │ - proactive_recall()│      │
│  │ - memory_type│                  └────────┬─────────┘         │
│  │ - content    │                           │                   │
│  │ - embedding  │                           ▼                   │
│  │ - metadata   │                  ┌──────────────────┐         │
│  └──────────────┘                  │ MCP Tools        │         │
│         │                          │                  │         │
│         │ pgvector                 │ - search_memory()│         │
│         ▼                          │   (reactive)     │         │
│  ┌──────────────┐                  └──────────────────┘         │
│  │  PostgreSQL  │                                               │
│  │  + pgvector  │                                               │
│  └──────────────┘                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Memory Types

| Type | Purpose | Example Content |
|------|---------|-----------------|
| `analysis_summary` | Condensed past analysis results | "React article: 5 security issues, performance tips..." |
| `vulnerability_pattern` | Known vulnerability patterns | "XSS via dangerouslySetInnerHTML in JSX" |
| `best_practice` | Learned best practices | "Always validate JWT expiration client-side" |
| `agent_finding` | Individual agent findings | Security auditor finding about SQL injection |

## Implementation Plan

### Phase 1: Database Model & Migration
- Create `AgentMemory` model with pgvector embedding
- Add indices for efficient similarity search
- Migration for new table

### Phase 2: Memory Service
- `AgentMemoryService` with store/search/proactive_recall
- Integration with existing EmbeddingService
- Memory scoping by analysis_id

### Phase 3: MCP Tool
- `search_memory` tool for reactive recall
- Tool registration in MCP registry
- Add capability to all agents

### Phase 4: Proactive Integration
- Inject relevant memories before agent execution
- Relevance threshold to avoid noise
- Update agent runner to include memories

## Files to Create/Modify

### New Files
- `backend/app/models/agent_memory.py` - SQLAlchemy model
- `backend/app/services/memory/agent_memory_service.py` - Memory service
- `backend/app/services/memory/__init__.py` - Module exports
- `backend/app/services/context/memory_tools.py` - MCP tools
- `backend/alembic/versions/xxx_add_agent_memory.py` - Migration
- `backend/tests/unit/services/memory/test_agent_memory_service.py` - Tests

### Modified Files
- `backend/app/services/mcp/registry.py` - Add memory tool capability
- `backend/app/workflows/tasks/runners.py` - Inject proactive memories
- `backend/app/schemas/__init__.py` - Export new schemas

## API Design

### AgentMemory Model
```python
class AgentMemory(Base):
    id: Mapped[UUID]
    analysis_id: Mapped[UUID]  # Foreign key to Analysis
    memory_type: Mapped[str]   # analysis_summary, vulnerability_pattern, etc.
    content: Mapped[str]       # The actual memory content
    embedding: Mapped[Vector]  # 1536-dim pgvector
    metadata: Mapped[dict]     # JSONB for flexible data
    created_at: Mapped[datetime]
```

### AgentMemoryService
```python
class AgentMemoryService:
    async def store(
        self,
        analysis_id: UUID,
        memory_type: MemoryType,
        content: str,
        metadata: dict | None = None,
    ) -> AgentMemory

    async def search(
        self,
        query: str,
        memory_type: MemoryType | None = None,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> list[MemorySearchResult]

    async def proactive_recall(
        self,
        content_summary: str,
        agent_type: str,
    ) -> list[MemorySnippet]
```

### MCP Tool
```python
@tool(args_schema=SearchMemoryInput)
async def search_memory(
    query: str,
    memory_type: str = "all",
    limit: int = 5,
) -> str:
    """Search past analyses and findings for relevant context."""
```

## Testing Strategy

### Unit Tests
- Memory storage and retrieval
- Embedding generation for memories
- Search with various filters
- Proactive recall logic

### Integration Tests
- End-to-end memory flow
- Agent using search_memory tool
- Proactive injection in workflow

## Success Criteria

- [ ] AgentMemory model with pgvector embedding
- [ ] AgentMemoryService with store/search/proactive_recall
- [ ] search_memory MCP tool available to all agents
- [ ] Proactive recall runs before agent invocation
- [ ] Relevance threshold prevents noise injection
- [ ] All tests passing
- [ ] CI checks passing (ruff format, ruff check, mypy)
