# Issue #92: Improve Content Extraction Error Handling

**Status:** 🔄 **OPEN**  
**Assignee:** Yonatan  
**Story Points:** 2 pts  
**Priority:** MEDIUM  
**GitHub Issue:** [#92](https://github.com/ArieGoldkin/SkillForge/issues/92)

---

## Issue Overview

**Title:** [🔵 Backend] Improve Content Extraction Error Handling [2 pts]

**Description:**  
JinaReaderError occurs for some URLs but error context is minimal. Multiple extraction failures observed in LangSmith traces with insufficient debugging information.

**Labels:** `🔵 backend`, `🐛 bug`, `extraction`, `jina`

---

## Problem Statement

### Error Pattern

```
JinaReaderError('Extraction failed')
```

### Observations

- Multiple `extract_content` failures in LangSmith traces
- Some appear to be from tests (`test-analysis-id`)
- Real extractions may also be failing
- **Error messages lack context:** No HTTP status, response details, or request URLs

### Failed Analyses

- `daabec4f-ee43-487e-af23-9457bf852ba2` (langgraph repo)
- `7ec3d8b2-e53f-44d4-9240-599a57321495` (anthropic article)
- All have 0 progress events = failed early

### Note

**JINA_API_KEY is confirmed in backend/.env**, so this is about error handling, not configuration.

---

## Solution

Improve error handling to provide better context for debugging extraction failures. Add detailed logging and more specific error messages.

### Implementation Approach

1. Add HTTP status codes to error messages
2. Log response bodies (sanitized) for debugging
3. Include request URLs in error context
4. Consider adding specific error types for different failure modes
5. Improve error messages in exception handling

---

## Files to Modify

### Primary Changes

- **`backend/app/services/extraction/jina_reader.py`**
  - Improve error messages in exception handlers
  - Add HTTP status codes to error context
  - Log response bodies (sanitized) and request URLs
  - Consider adding specific error types (404, timeout, rate limit)

- **`backend/app/workflows/tasks.py`** (optional)
  - Improve `extract_content` task error handling
  - Add more context to error propagation

### Testing

- **`backend/tests/unit/test_jina_reader.py`**
  - Update tests to cover improved error handling
  - Test various failure scenarios (404, timeout, rate limit)

---

## Acceptance Criteria

- [ ] Add more detailed error context to JinaReaderError messages
- [ ] Log HTTP status codes, response bodies (sanitized), and request URLs
- [ ] Verify error handling works for various failure scenarios
- [ ] Consider adding specific error types for different failure modes (404, timeout, rate limit)
- [ ] Update tests to cover improved error handling
- [ ] Verify error messages are helpful for debugging

---

## Technical Details

### Current Implementation

```python
# backend/app/services/extraction/jina_reader.py
# Error messages are generic:
raise JinaReaderError("Extraction failed")
raise JinaReaderError("URL not found")
raise JinaReaderError("HTTP 500")
```

### Proposed Implementation

```python
# More detailed error messages with context
if response.status_code == 404:
    error_msg = (
        f"URL not found (404): {url}. "
        f"Response: {response.text[:200]}"
    )
    logger.error(
        "jina_extraction_not_found",
        url=url,
        status_code=404,
        response_preview=response.text[:200],
    )
    raise JinaReaderError(error_msg)

# For timeouts
except httpx.TimeoutException as e:
    error_msg = (
        f"Request timed out after {timeout}s: {url}. "
        f"Error: {str(e)}"
    )
    logger.exception(
        "jina_extraction_timeout",
        url=url,
        timeout=timeout,
        error=str(e),
    )
    raise JinaReaderError(error_msg) from e

# For generic errors
except Exception as e:
    error_msg = (
        f"Extraction failed for {url}: {type(e).__name__}: {str(e)}"
    )
    logger.exception(
        "jina_extraction_failed",
        url=url,
        error=str(e),
        error_type=type(e).__name__,
        exc_info=True,
    )
    raise JinaReaderError(error_msg) from e
```

### Optional: Specific Error Types

```python
# backend/app/core/exceptions.py
class JinaReaderNotFoundError(JinaReaderError):
    """Raised when URL returns 404."""
    pass

class JinaReaderTimeoutError(JinaReaderError):
    """Raised when request times out."""
    pass

class JinaReaderRateLimitError(JinaReaderError):
    """Raised when rate limited."""
    pass
```

---

## Related Issues

- **Issue #4:** Content Extraction (Jina AI) (original implementation)
- Discovered during system health analysis using LangSmith MCP

---

## Verification

After implementation:

1. **Unit Tests:** Run Jina Reader tests with various error scenarios
2. **Integration Tests:** Test with real URLs that fail (404, timeout)
3. **LangSmith:** Verify error traces contain detailed context
4. **Manual Test:** Trigger extraction failure and verify error message is helpful

---

## Notes

- Error messages should be helpful but not expose sensitive data
- Sanitize response bodies before logging (remove API keys, tokens)
- Consider rate limit detection and retry logic improvements
- Monitor error patterns to identify common failure modes
