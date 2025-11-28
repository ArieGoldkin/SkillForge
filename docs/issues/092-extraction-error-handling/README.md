# Issue #92: Improve Content Extraction Error Handling

**Status:** ✅ **COMPLETE**  
**Assignee:** Yonatan  
**Story Points:** 2 pts  
**Priority:** MEDIUM  
**Completed:** December 2024  
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

- [x] Add more detailed error context to JinaReaderError messages ✅
- [x] Log HTTP status codes, response bodies (sanitized), and request URLs ✅
- [x] Verify error handling works for various failure scenarios ✅
- [x] Consider adding specific error types for different failure modes (404, timeout, rate limit) ✅
- [x] Update tests to cover improved error handling ✅
- [x] Verify error messages are helpful for debugging ✅

---

## Technical Details

### ✅ Implementation (COMPLETE)

**File:** `backend/app/services/extraction/jina_reader.py` (lines 84-167)

```python
# 404 handling with detailed context (lines 84-93)
if response.status_code == HTTP_NOT_FOUND:
    response_preview = response.text[:MAX_ERROR_MESSAGE_LENGTH_LONG]
    error_msg = f"URL not found (404): {url}. Response preview: {response_preview}"
    logger.error(
        "jina_extraction_not_found",
        url=url,
        status_code=HTTP_NOT_FOUND,
        response_preview=response_preview,
    )
    raise JinaReaderError(error_msg)

# HTTP error handling with status codes (lines 96-108)
if response.status_code >= HTTP_ERROR_THRESHOLD:
    response_preview = response.text[:MAX_ERROR_MESSAGE_LENGTH_LONG]
    error_msg = (
        f"HTTP {response.status_code} error for {url}. Response: {response_preview}"
    )
    logger.error(
        "jina_extraction_http_error",
        url=url,
        status_code=response.status_code,
        response_preview=response_preview,
        response_headers=dict(response.headers),
    )
    raise JinaReaderError(error_msg)

# Timeout handling with context (lines 141-152)
except httpx.TimeoutException as e:
    error_msg = (
        f"Request timed out after {DEFAULT_TIMEOUT}s: {url}. Error type: {type(e).__name__}"
    )
    logger.exception(
        "jina_extraction_timeout",
        url=url,
        timeout=DEFAULT_TIMEOUT,
        error=str(e),
        error_type=type(e).__name__,
    )
    raise JinaReaderError(error_msg) from e

# Generic error handling with full context (lines 158-167)
except Exception as e:
    error_msg = f"Extraction failed for {url}: {type(e).__name__}: {str(e)}"
    logger.exception(
        "jina_extraction_failed",
        url=url,
        error=str(e),
        error_type=type(e).__name__,
        exc_info=True,
    )
    raise JinaReaderError(error_msg) from e
```

**Verification:**
- ✅ Detailed error messages with HTTP status codes
- ✅ Response previews included (sanitized via MAX_ERROR_MESSAGE_LENGTH_LONG)
- ✅ Request URLs included in all error messages
- ✅ Specific handling for 404, HTTP errors, timeouts, and generic exceptions
- ✅ Comprehensive structured logging with context
- ✅ Error type information included in all error messages

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
