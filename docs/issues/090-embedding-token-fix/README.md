# Issue #90: Fix Embedding Token Limit Violation

**Status:** 🔄 **OPEN**  
**Assignee:** Yonatan  
**Story Points:** 5 pts  
**Priority:** HIGH  
**GitHub Issue:** [#90](https://github.com/ArieGoldkin/SkillForge/issues/90)

---

## Issue Overview

**Title:** [🔵 Backend] Fix Embedding Token Limit Violation [5 pts]

**Description:**  
Embedding service uses character-based truncation (32,000 chars) but OpenAI model limit is 8,192 tokens. Character-to-token ratio varies, causing token limit violations and workflow failures.

**Labels:** `🔵 backend`, `🐛 bug`, `🔥 critical`, `embeddings`, `openai`

---

## Problem Statement

### Error from LangSmith

```
This model's maximum context length is 8192 tokens, however you requested 8974 tokens
```

### Root Cause

- **File:** `backend/app/services/embeddings.py:63`
- **Issue:** `max_text_length = 32_000` assumes ~8,191 tokens
- **Problem:** Character-to-token conversion is not 1:1 (varies by language, content type)
- **Impact:** Code truncates by characters, not tokens → Token limit exceeded → EmbeddingError

### Evidence

- **Failed analysis:** `daabec4f-ee43-487e-af23-9457bf852ba2`
- **URL:** https://github.com/langchain-ai/langgraph
- **Content:** Large GitHub README (exceeded token limit)
- **Error:** 8974 tokens requested, 8192 max

### Impact

- Workflow failures for large content
- Embedding generation fails silently or with errors
- Affects analyses of large documents/repositories

---

## Solution

Use `tiktoken` to count tokens instead of characters. `tiktoken` is already in `poetry.lock` but not being used.

### Implementation Approach

1. Import `tiktoken` and get encoding for `text-embedding-3-small`
2. Replace character-based truncation with token-based truncation
3. Truncate to 8,000 tokens (safety margin below 8,192 limit)
4. Update logging to show token count instead of character count

---

## Files to Modify

### Primary Changes

- **`backend/app/services/embeddings.py`**
  - Line 63: Update `max_text_length` to token-based limit
  - Lines 101-109: Replace character truncation with token truncation
  - Add tiktoken import and token counting logic

### Testing

- **`backend/tests/unit/test_embeddings.py`** (or create new test file)
  - Add unit tests for token-based truncation
  - Test with various content types (English, code, mixed)
  - Verify truncation respects 8,000 token limit

---

## Acceptance Criteria

- [ ] Use tiktoken to count tokens instead of characters
- [ ] Truncate to 8,000 tokens (safety margin below 8,192 limit)
- [ ] Add unit tests for token-based truncation
- [ ] Verify no token limit errors in LangSmith traces
- [ ] Update docstring to reflect token-based truncation
- [ ] Update logging to show token count (not just character count)

---

## Technical Details

### Current Implementation

```python
# backend/app/services/embeddings.py:63
self.max_text_length = 32_000  # ~8,191 tokens (OpenAI limit)

# Lines 101-109
if len(text) > self.max_text_length:
    text = text[: self.max_text_length]
    logger.warning(
        "embedding_text_truncated",
        original_length=original_length,
        truncated_length=self.max_text_length,
    )
```

### Proposed Implementation

```python
import tiktoken

# In __init__
self.model = "text-embedding-3-small"
self.max_tokens = 8_000  # Safety margin below 8,192 limit
self.encoding = tiktoken.encoding_for_model("text-embedding-3-small")

# In generate_embedding
tokens = self.encoding.encode(text)
if len(tokens) > self.max_tokens:
    tokens = tokens[: self.max_tokens]
    text = self.encoding.decode(tokens)
    logger.warning(
        "embedding_text_truncated",
        original_tokens=len(tokens),
        truncated_tokens=self.max_tokens,
    )
```

---

## Related Issues

- **Issue #5:** Embedding Service Implementation (original implementation)
- Discovered during system health analysis using LangSmith MCP

---

## Verification

After implementation:

1. **Unit Tests:** Run embedding service tests
2. **Integration Tests:** Test with large content (GitHub README)
3. **LangSmith:** Verify no token limit errors in traces
4. **Manual Test:** Analyze large document and verify embedding succeeds

---

## Notes

- `tiktoken` is already in `poetry.lock` (no new dependency needed)
- Token counting is more accurate than character counting
- 8,000 token limit provides safety margin (192 tokens buffer)
- Consider caching encoding object for performance
