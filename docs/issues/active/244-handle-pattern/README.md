# Issue #244: Handle Pattern for Large Payloads

**Sprint:** 11 - Context Engineering
**Story Points:** 5
**Priority:** HIGH
**Status:** In Progress
**Branch:** `feature/sprint-11-context-engineering`

---

## Overview

Implement the **Handle Pattern** from Google ADK's Context Engineering framework. Large payloads (`raw_content`, embeddings) are stored as references and loaded on-demand rather than passed inline through agent state.

**Source:** [Google ADK Context Engineering](https://google.github.io/adk-docs/sessions/context-engineering/)

---

## Problem Statement

### Current Architecture (Problematic)

```
┌─────────────────────────────────────────────────────────────────┐
│  AnalysisState (Passed to ALL 8 agents via Send API)            │
├─────────────────────────────────────────────────────────────────┤
│  raw_content: "... 50KB of article text ..."     ← INLINE       │
│  content_embedding: [...1536 floats...]          ← INLINE       │
│  extraction_metadata: {...}                                      │
│  supervisor_decision: {...}                                      │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼ (8 parallel copies)
    ┌───────────────┬───────────────┬───────────────┐
    │ tech_comparator│ security_auditor│ ...6 more  │
    │ Gets 50KB     │ Gets 50KB      │ Gets 50KB   │
    └───────────────┴───────────────┴───────────────┘
```

**Issues:**
- **Memory explosion:** 50KB × 8 agents = 400KB in parallel execution
- **Lost in the middle:** Agents struggle with large inline content
- **Token waste:** Each LLM call includes full content in context
- **Checkpoint bloat:** LangGraph stores full state after each node

### Target Architecture (Handle Pattern)

```
┌─────────────────────────────────────────────────────────────────┐
│  AnalysisState (Lightweight refs only)                          │
├─────────────────────────────────────────────────────────────────┤
│  content_ref: {                                                  │
│    uri: "analysis://abc-123/content",                           │
│    summary: "Article about React Server Components...",          │
│    size_bytes: 45000,                                            │
│    sections: ["intro", "implementation", "code_blocks"]          │
│  }                                                               │
│  supervisor_decision: {...}                                      │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼ (Lightweight state to all agents)
    ┌───────────────┬───────────────┬───────────────┐
    │ tech_comparator│ security_auditor│ ...6 more  │
    │ Gets ~500 tok │ Gets ~500 tok  │ Gets ~500 tok│
    │               │                │              │
    │ load_artifact │ load_artifact  │ (may not    │
    │ "code_blocks" │ "full"         │  need full) │
    └───────────────┴───────────────┴───────────────┘
```

---

## Design Decisions

### 1. Storage Approach: Database-Only

**Decision:** Use existing PostgreSQL Analysis table with added columns.

**Rationale:**
- Already have `raw_content` column in Analysis table
- No new infrastructure required
- Atomic transactions for content + refs
- Simple backup/restore (single data source)
- Content typically <500KB (articles, not files)

**Alternatives Considered:**
| Approach | Rejected Because |
|----------|-----------------|
| Hybrid DB+File | Overkill for <1MB content, adds cleanup complexity |
| S3/Object Storage | Unnecessary network hops, overkill for current scale |
| Full Abstraction Layer | YAGNI - can refactor later if needed |

### 2. Access Pattern: MCP Tool

**Decision:** Agents access content via `load_artifact` MCP tool.

**Rationale:**
- Aligns with Sprint 9 MCP infrastructure
- Reactive pattern - agent decides when/what to load
- Explicit over magic (no hidden lazy-loading)
- Enables section-based partial loading

---

## Technical Design

### 1. ArtifactRef Schema

```python
# backend/app/schemas/artifact.py

class ArtifactSection(str, Enum):
    """Available sections for partial loading."""
    FULL = "full"                 # Complete content
    SUMMARY = "summary"           # LLM-generated summary (~500 tokens)
    FIRST_N = "first_n"           # First N characters
    CODE_BLOCKS = "code_blocks"   # Extracted code snippets
    HEADINGS = "headings"         # Document structure


class ArtifactRef(BaseModel):
    """Reference to large content stored externally."""
    uri: str                      # analysis://{analysis_id}/content
    summary: str                  # Always-available summary
    size_bytes: int               # Original content size
    content_type: str             # text/plain, text/markdown, etc.
    sections: list[ArtifactSection]  # Available sections

    model_config = ConfigDict(frozen=True)
```

### 2. Database Migration

```sql
-- Add columns to analysis table
ALTER TABLE analysis ADD COLUMN content_summary TEXT;
ALTER TABLE analysis ADD COLUMN content_sections JSONB DEFAULT '{}';

-- content_sections structure:
-- {
--   "code_blocks": [{"start": 0, "end": 500, "language": "python"}, ...],
--   "headings": [{"level": 1, "text": "Introduction", "start": 0}, ...],
--   "word_count": 5000
-- }
```

### 3. ArtifactStore Service

```python
# backend/app/services/context/artifact_store.py

class ArtifactStore:
    """Database-backed artifact storage with section loading."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_ref(
        self,
        analysis_id: str,
        content: str,
        content_type: str = "text/plain"
    ) -> ArtifactRef:
        """Store content and return lightweight ref with summary."""
        # 1. Generate summary via LLM (or extraction)
        summary = await self._generate_summary(content)

        # 2. Extract sections (code blocks, headings)
        sections = await self._extract_sections(content)

        # 3. Update analysis record
        await self._update_analysis(
            analysis_id,
            content_summary=summary,
            content_sections=sections
        )

        # 4. Return ref (content already in raw_content column)
        return ArtifactRef(
            uri=f"analysis://{analysis_id}/content",
            summary=summary,
            size_bytes=len(content.encode()),
            content_type=content_type,
            sections=list(sections.keys())
        )

    async def load(
        self,
        uri: str,
        section: ArtifactSection = ArtifactSection.SUMMARY,
        max_chars: int | None = None
    ) -> str:
        """Load content or section from artifact."""
        analysis_id = self._parse_uri(uri)

        match section:
            case ArtifactSection.SUMMARY:
                return await self._load_summary(analysis_id)
            case ArtifactSection.FULL:
                return await self._load_full(analysis_id, max_chars)
            case ArtifactSection.CODE_BLOCKS:
                return await self._load_code_blocks(analysis_id)
            case ArtifactSection.HEADINGS:
                return await self._load_headings(analysis_id)
            case ArtifactSection.FIRST_N:
                return await self._load_first_n(analysis_id, max_chars or 5000)
```

### 4. State Changes

```python
# backend/app/workflows/state.py

class AnalysisState(TypedDict, total=False):
    analysis_id: AnalysisID
    url: str
    content_type: str
    skill_level: str

    # BEFORE: Large inline content
    # raw_content: str  # ❌ REMOVED from state
    # content_embedding: EmbeddingVector  # ❌ REMOVED from state

    # AFTER: Lightweight refs
    content_ref: dict  # ArtifactRef as dict for JSON serialization

    # ... rest unchanged
    extraction_metadata: dict[str, object]
    supervisor_decision: dict[str, object]
    agent_findings: Annotated[list[dict[str, object]], operator.add]
    aggregated_insights: dict[str, object]
```

### 5. MCP Tool for Agents

```python
# backend/app/services/mcp/tools/artifacts.py

@mcp.tool()
async def load_artifact(
    uri: str,
    section: Literal["full", "summary", "code_blocks", "headings", "first_n"] = "summary",
    max_chars: int | None = None
) -> str:
    """
    Load content from artifact storage.

    Args:
        uri: Artifact URI (e.g., "analysis://abc-123/content")
        section: Which section to load:
            - "summary": Quick overview (~500 tokens) - DEFAULT
            - "full": Complete content (use sparingly)
            - "code_blocks": Only code snippets
            - "headings": Document structure
            - "first_n": First N characters
        max_chars: Limit for full/first_n sections

    Returns:
        Requested content section as string.

    Example:
        # Get overview first
        summary = await load_artifact(uri, "summary")

        # If needed, load specific section
        code = await load_artifact(uri, "code_blocks")
    """
    async with get_session() as session:
        store = ArtifactStore(session)
        return await store.load(uri, ArtifactSection(section), max_chars)
```

### 6. Workflow Integration

```python
# backend/app/workflows/nodes/extract.py

async def _extract_content_node(state: AnalysisState) -> dict:
    """Extract content and create artifact ref."""
    url = state["url"]
    analysis_id = state["analysis_id"]

    # 1. Extract raw content (existing logic)
    result = await extract_content(url, analysis_id)
    raw_content = result["raw_content"]

    # 2. Store in DB and create ref (NEW)
    async with get_session() as session:
        store = ArtifactStore(session)
        content_ref = await store.create_ref(
            analysis_id=analysis_id,
            content=raw_content,
            content_type=result.get("content_type", "text/plain")
        )

    # 3. Return ref instead of raw content
    return {
        "content_ref": content_ref.model_dump(),  # Lightweight ref
        "extraction_metadata": result["extraction_metadata"],
        "content_type": result.get("content_type"),
    }
```

---

## Migration Strategy

### Phase 1: Add Infrastructure (This PR)
1. Add `content_summary` and `content_sections` columns
2. Create `ArtifactStore` service
3. Create `load_artifact` MCP tool
4. Update `AnalysisState` type

### Phase 2: Update Extraction Node
1. Modify `_extract_content_node` to create refs
2. Keep `raw_content` in DB (already there)
3. Generate summary during extraction

### Phase 3: Update Agent Nodes
1. Update agents to use `content_ref` instead of `raw_content`
2. Agents call `load_artifact` tool when needed
3. Summary always available without tool call

### Phase 4: Backwards Compatibility
1. Handle existing analyses without refs
2. Lazy-create refs on first access for old data

---

## File Changes

### New Files
- [ ] `backend/app/schemas/artifact.py` - ArtifactRef schema
- [ ] `backend/app/services/context/__init__.py` - Context services package
- [ ] `backend/app/services/context/artifact_store.py` - ArtifactStore service
- [ ] `backend/app/services/mcp/tools/artifacts.py` - load_artifact tool
- [ ] `backend/alembic/versions/xxx_add_content_summary.py` - Migration

### Modified Files
- [ ] `backend/app/workflows/state.py` - Add content_ref, keep raw_content for now
- [ ] `backend/app/workflows/nodes/extract.py` - Create refs during extraction
- [ ] `backend/app/core/types.py` - Add ArtifactRef type alias

### Test Files
- [ ] `backend/tests/unit/services/context/test_artifact_store.py`
- [ ] `backend/tests/unit/services/mcp/tools/test_artifacts.py`
- [ ] `backend/tests/integration/context/test_artifact_workflow.py`

---

## Acceptance Criteria

- [ ] `ArtifactRef` schema defined with uri, summary, sections
- [ ] Large content (>5KB) stored in DB, refs in state
- [ ] `load_artifact` MCP tool available to agents
- [ ] Agents default to summary, explicitly request full when needed
- [ ] Summary generation during extraction
- [ ] Migration script for new columns
- [ ] Unit tests for ArtifactStore (>80% coverage)
- [ ] Integration test: full workflow with refs

---

## Testing Plan

### Unit Tests
```python
# test_artifact_store.py
def test_create_ref_generates_summary()
def test_create_ref_extracts_code_blocks()
def test_load_summary_returns_cached()
def test_load_full_respects_max_chars()
def test_load_code_blocks_extracts_correctly()
def test_invalid_uri_raises_error()
```

### Integration Tests
```python
# test_artifact_workflow.py
async def test_extraction_creates_ref()
async def test_agent_can_load_via_tool()
async def test_backwards_compat_old_analyses()
```

---

## Metrics & Success Criteria

| Metric | Before | Target | Measurement |
|--------|--------|--------|-------------|
| State size per agent | ~50KB | ~2KB | Log state size in agent nodes |
| Checkpoint size | ~400KB | ~50KB | Monitor LangGraph checkpoints |
| Agent context tokens | ~15K | ~3K | Track via LangSmith |

---

## References

- [Google ADK Context Engineering](https://google.github.io/adk-docs/sessions/context-engineering/)
- [Issue #244 on GitHub](https://github.com/ArieGoldkin/SkillForge/issues/244)
- [Sprint 11 Epic #248](https://github.com/ArieGoldkin/SkillForge/issues/248)
