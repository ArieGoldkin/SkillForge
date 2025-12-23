# raw_content vs content_ref Usage Guide

**Date**: December 22, 2025  
**Purpose**: Clarify when to use `raw_content` vs `content_ref` in the workflow

---

## 🎯 Core Principle

Both `raw_content` and `content_ref` serve different purposes and should coexist:

- **`raw_content`**: Full content string - used for operations that need the entire content inline
- **`content_ref`**: Lightweight reference (Handle Pattern) - used for on-demand loading via ArtifactStore

---

## 📊 Usage Patterns

### When to Use `raw_content`

**Use `raw_content` for operations that need the FULL content inline:**

```
┌─────────────────────────────────────────────────────────────────┐
│              OPERATIONS THAT USE raw_content                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Embedding Generation                                        │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Reason: Needs full content to generate embedding       │ │
│     │ Location: _generate_embedding_node()                   │ │
│     │ Code: content = state["raw_content"]                   │ │
│     └────────────────────────────────────────────────────────┘ │
│                                                                  │
│  2. Chunking Operations                                         │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Reason: Needs full content to split into chunks        │ │
│     │ Location: _chunk_and_embed_node()                      │ │
│     │ Code: content = state["raw_content"]                   │ │
│     └────────────────────────────────────────────────────────┘ │
│                                                                  │
│  3. Context Injection (Memory Recall)                          │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Reason: Needs full content for similarity search       │ │
│     │ Location: inject_context_node()                        │ │
│     │ Code: raw_content = state.get("raw_content", "")       │ │
│     └────────────────────────────────────────────────────────┘ │
│                                                                  │
│  4. Quality Gate Evaluation                                    │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Reason: Needs full content for quality scoring         │ │
│     │ Location: quality_gate_node()                          │ │
│     │ Code: input_content = state.get("raw_content", "")     │ │
│     └────────────────────────────────────────────────────────┘ │
│                                                                  │
│  5. Database Persistence (via ArtifactStore)                   │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Reason: Must store full content for load() to retrieve │ │
│     │ Location: ArtifactStore.create_ref()                   │ │
│     │ Note: Stored in Analysis.raw_content column            │ │
│     └────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### When to Use `content_ref` (Handle Pattern)

**Use `content_ref` for operations that can load content on-demand:**

```
┌─────────────────────────────────────────────────────────────────┐
│              OPERATIONS THAT USE content_ref                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Agent Execution (All Agents)                                │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Reason: Agents load only what they need (sections)     │ │
│     │ Location: All agent nodes (trend_validator, etc.)      │ │
│     │ Pattern:                                                │ │
│     │   1. Check content_ref (preferred)                      │ │
│     │   2. Load via ArtifactStore.load(uri, section)         │ │
│     │   3. Fallback to raw_content if needed                  │ │
│     │ Benefit: Reduced token usage, faster agent execution   │ │
│     └────────────────────────────────────────────────────────┘ │
│                                                                  │
│  2. Workflow State Passing                                     │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Reason: Avoid passing large strings through state      │ │
│     │ Benefit: Lightweight state (~200 bytes vs MBs)         │ │
│     │ Pattern: Store ref, load on-demand                     │ │
│     └────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Current Implementation Flow

### Extraction Node (Creates Both)

```
┌─────────────────────────────────────────────────────────────────┐
│              EXTRACTION NODE OUTPUT                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  extract_content_node() returns:                                │
│  {                                                              │
│    "raw_content": "...",           # Full content string        │
│    "content_ref": {               # Handle Pattern ref          │
│      "uri": "analysis://{id}/content",                          │
│      "summary": "...",                                          │
│      "size_bytes": 45000,                                       │
│      "content_type": "text/markdown",                           │
│      "available_sections": ["summary", "full", ...]             │
│    },                                                            │
│    "extraction_metadata": {...}                                 │
│  }                                                              │
│                                                                  │
│  ArtifactStore.create_ref():                                    │
│    - Stores raw_content in Analysis.raw_content (DB)            │
│    - Creates content_ref with URI                               │
│    - Generates summary and section metadata                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Embedding Node (Uses raw_content)

```
┌─────────────────────────────────────────────────────────────────┐
│              EMBEDDING NODE                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  _generate_embedding_node(state):                              │
│    content = state["raw_content"]  # ⭐ Needs full content      │
│    embedding = await generate_embedding(content, analysis_id)  │
│    return {"content_embedding": embedding}                     │
│                                                                  │
│  Why raw_content?                                               │
│  - Embedding service needs full content                         │
│  - Cannot use sections (embedding is for entire content)       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Nodes (Use content_ref with Fallback)

```
┌─────────────────────────────────────────────────────────────────┐
│              AGENT NODE PATTERN                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  trend_validator_node(state):                                  │
│    # Check availability                                        │
│    if not has_content_available(state):                        │
│        # Check both content_ref and raw_content                │
│        return {}                                               │
│                                                                  │
│    # Run agent with Handle Pattern                             │
│    result = await run_agent(                                    │
│        content=get_fallback_content(state)  # Loads via ref    │
│    )                                                            │
│                                                                  │
│  get_fallback_content(state):                                  │
│    # 1. Try content_ref (preferred)                            │
│    if content_ref := state.get("content_ref"):                 │
│        # Load via ArtifactStore                                │
│        return await store.load(uri, section="full")            │
│                                                                  │
│    # 2. Fallback to raw_content                                │
│    return state.get("raw_content", "")                         │
│                                                                  │
│  Why content_ref?                                               │
│  - Agents can load only needed sections                        │
│  - Reduces token usage                                         │
│  - Faster execution                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✅ Validation Strategy

### For Completed Workflows

```
┌─────────────────────────────────────────────────────────────────┐
│              VALIDATION REQUIREMENTS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ REQUIRED: content_ref                                       │
│     - Must exist and be valid                                   │
│     - URI must point to existing content                        │
│     - All fields present (uri, summary, size_bytes, etc.)      │
│                                                                  │
│  ✅ REQUIRED: raw_content                                       │
│     - Must exist in database (stored by ArtifactStore)        │
│     - Used by nodes that need full content                      │
│     - Used by ArtifactStore.load() to retrieve content         │
│                                                                  │
│  ⚠️ Both are required but serve different purposes:            │
│     - content_ref: For workflow state and agent loading        │
│     - raw_content: For embedding, chunking, DB storage         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Validation Logic

```python
class WorkflowResult(BaseModel):
    """Validated workflow result schema."""
    
    # Both required for completed workflows
    content_ref: ContentRef  # For Handle Pattern (agents, state passing)
    raw_content: str | None = None  # For operations needing full content
    
    def validate_for_status(self, status: str) -> list[str]:
        """Validate required fields for given status."""
        missing: list[str] = []
        
        if status == "completed":
            # Both required - serve different purposes
            if not self.content_ref:
                missing.append("content_ref")  # For Handle Pattern
            # raw_content should exist in DB (stored by ArtifactStore)
            # We validate it exists, but don't require it in state
            # (it's stored in DB, not passed through state)
            
        return missing
```

---

## 📋 Summary: When to Use What

### Use `raw_content` when:

1. ✅ **Embedding generation** - needs full content
2. ✅ **Chunking operations** - needs full content to split
3. ✅ **Quality gate evaluation** - needs full content for scoring
4. ✅ **Context injection** - needs full content for similarity search
5. ✅ **Database storage** - ArtifactStore stores it for load()
6. ✅ **Fallback for agents** - if content_ref unavailable

### Use `content_ref` when:

1. ✅ **Agent execution** - agents load sections on-demand
2. ✅ **Workflow state passing** - lightweight state (~200 bytes)
3. ✅ **Partial content loading** - load only needed sections
4. ✅ **Token optimization** - reduce token usage in agent calls

### Both are needed because:

- `raw_content`: Required for operations needing full content inline
- `content_ref`: Required for efficient state passing and on-demand loading
- **Coexistence**: Both serve different purposes and complement each other

---

## 🔧 Current Issues & Recommendations

### Issue: Validator Only Checks `raw_content`

**Current**:
```python
required_fields = ["raw_content", "extraction_metadata", "content_embedding"]
```

**Should be**:
```python
# For completed workflows:
# - content_ref is REQUIRED (for Handle Pattern)
# - raw_content exists in DB (stored by ArtifactStore)
# - Both serve different purposes
```

### Recommendation: Validate Both

1. **Validate `content_ref` exists and is valid** (for Handle Pattern)
2. **Verify `raw_content` exists in database** (stored by ArtifactStore)
3. **Both are required** but serve different purposes:
   - `content_ref`: For workflow state and agent loading
   - `raw_content`: For embedding, chunking, and DB retrieval

---

## 🎯 Best Practice Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│              RECOMMENDED USAGE PATTERN                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Extraction Node:                                               │
│    ✅ Create both raw_content and content_ref                   │
│    ✅ Store raw_content in DB via ArtifactStore                │
│    ✅ Return both in state                                      │
│                                                                  │
│  Embedding/Chunking Nodes:                                      │
│    ✅ Use raw_content (needs full content)                     │
│                                                                  │
│  Agent Nodes:                                                   │
│    ✅ Prefer content_ref (load on-demand)                      │
│    ✅ Fallback to raw_content if needed                         │
│                                                                  │
│  Validation:                                                    │
│    ✅ Validate content_ref exists and is valid                 │
│    ✅ Verify raw_content exists in DB                          │
│    ✅ Both required for completed workflows                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

**Key Takeaway**: `raw_content` and `content_ref` are complementary, not mutually exclusive. Both are needed for different operations in the workflow.
