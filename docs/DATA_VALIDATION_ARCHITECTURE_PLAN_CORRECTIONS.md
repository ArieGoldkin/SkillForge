# Data Validation Plan - Corrections for raw_content vs content_ref

**Date**: December 22, 2025  
**Purpose**: Summary of corrections needed to reflect correct usage

---

## 🎯 Key Corrections Needed

### Section 1: Schema Definition (Line ~270)

**Current (WRONG)**:
```python
raw_content: str | None = None  # ⚠️ DEPRECATED (for backward compat)
```

**Should be**:
```python
raw_content: str = Field(..., min_length=1)  # For embedding, chunking
```

### Section 2: Validation Logic (Line ~318)

**Current (WRONG)**:
```python
# raw_content not required (deprecated)
```

**Should be**:
```python
# Both content_ref and raw_content required
# (serve different purposes - Issue #244)
if not self.content_ref:
    missing.append("content_ref")  # For Handle Pattern
if not self.raw_content:
    missing.append("raw_content")  # For embedding/chunking
```

### Section 3: Status Requirements (Line ~160)

**Current (INCOMPLETE)**:
```python
Status: "completed"
Required:
  ✅ raw_content (non-empty)
```

**Should be**:
```python
Status: "completed"
Required:
  ✅ content_ref (Handle Pattern - for agents, state passing)
  ✅ raw_content (for embedding, chunking, quality gate)
```

### Section 4: Persister Logic (Line ~527)

**Current (WRONG)**:
```python
analysis.raw_content = validated.raw_content
```

**Should be**:
```python
# Note: raw_content is already stored by ArtifactStore.create_ref()
# during extraction. We validate it exists but don't re-store.
# However, we still need raw_content in state for:
# - Embedding generation (needs full content)
# - Chunking operations (needs full content)
# - Quality gate evaluation (needs full content)
```

### Section 5: Read Validation (Line ~586)

**Current (INCOMPLETE)**:
```python
if not analysis.raw_content:
    errors.append("complete analysis missing raw_content")
```

**Should be**:
```python
# Handle Pattern: Check content_ref exists (via content_summary)
if not analysis.content_summary:
    errors.append("complete analysis missing content_summary (content_ref not created)")
# raw_content required for embedding, chunking, quality gate
if not analysis.raw_content:
    errors.append("complete analysis missing raw_content (required for embedding/chunking)")
```

---

## 📝 Summary

**Both `raw_content` and `content_ref` are REQUIRED for completed workflows** because they serve different purposes:

- **`content_ref`**: Handle Pattern - for agent execution, state passing (on-demand loading)
- **`raw_content`**: Full content - for embedding generation, chunking, quality gate (operations needing full content inline)

Neither is deprecated - both are essential and complementary.
