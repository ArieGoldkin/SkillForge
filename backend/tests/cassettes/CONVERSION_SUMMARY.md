# VCR Conversion Summary

## Overview

Converted Tavily Search tests from mock-based to VCR-based for deterministic HTTP replay.

**Date**: December 27, 2025
**Issue**: #433 - 2025 Best Practices
**Files Modified**:
- `tests/unit/services/tools/test_tavily_search.py`
- `tests/cassettes/README.md`
- `tests/cassettes/VCR_TESTING_GUIDE.md` (new)
- `scripts/record_vcr_cassettes.sh` (new)

## Tests Converted to VCR (8 total)

| Test | Query | Purpose |
|------|-------|---------|
| `test_search_success` | "Python best practices 2025" | Basic search functionality |
| `test_search_basic_depth` | "FastAPI async patterns" | Basic search depth parameter |
| `test_search_advanced_depth` | "LangGraph workflow examples" | Advanced search depth parameter |
| `test_search_query_truncation` | 700-char query | Query truncation to 400 chars |
| `test_search_custom_max_results` | "TypeScript best practices" | Custom max_results=10 |
| `test_search_include_raw_content` | "React Server Components" | Include raw content parameter |
| `test_search_include_images` | "Next.js 15 features" | Include images parameter |
| `test_search_no_answer` | "PostgreSQL indexing" | Exclude answer (include_answer=False) |

## Tests Kept as Mocks (15 total)

The following tests are intentionally kept as mock-based because they test:
- **Error handling**: 429 rate limit, 500 server error, 401 unauthorized, timeout, exceptions
- **Redis cache logic**: Cache hits, cache misses, cache key generation
- **Client-side validation**: Empty query, whitespace query, missing API key
- **Service lifecycle**: Client close, cache error handling

These scenarios don't benefit from VCR because:
1. We control the error conditions (not real API errors)
2. They test Redis integration (separate from HTTP API)
3. They validate client-side logic before HTTP calls

## VCR Configuration

**Location**: `tests/conftest.py` (lines 708-787)

**Key features**:
- **Record mode**: `once` (default), `none` in CI
- **Cassette directory**: `tests/cassettes/unit/tavily_search/`
- **Matching**: method + URI
- **Filtered headers**: authorization, x-api-key, api-key, x-tavily-api-key
- **Filtered params**: api_key, token, access_token
- **Custom redaction**: `redact_api_keys()` function

## Security Measures

1. **Automatic filtering** of sensitive headers and query params
2. **Custom redaction function** for request bodies
3. **CI enforcement** - fails if API keys leak
4. **Recording script** with built-in security checks

## Recording Workflow

### Quick Start
```bash
cd backend

# Record all Tavily tests
export TAVILY_API_KEY=your-key
VCR_RECORD_MODE=all pytest tests/unit/services/tools/test_tavily_search.py -v

# Or use the helper script
export TAVILY_API_KEY=your-key
./scripts/record_vcr_cassettes.sh
```

### Script Features
- Validates API key is set
- Records cassettes with proper mode
- Runs security checks for leaked keys
- Shows clear success/failure messages
- Provides next steps

## Benefits

### Before (Mock-based)
```python
@pytest.mark.asyncio
async def test_search_success(tavily_search):
    # Manual mock setup (30 lines)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {...}  # Fake data
    tavily_search.client.post = AsyncMock(return_value=mock_response)

    # Test uses fake response
    result = await tavily_search.search("test query")
    assert result["answer"] == "Test answer"  # Fragile
```

**Issues**:
- Manual mock setup is verbose
- Fake data doesn't match real API
- Tests break when API response format changes
- No guarantee mocks reflect reality

### After (VCR-based)
```python
@pytest.mark.asyncio
@pytest.mark.vcr()
async def test_search_success(tavily_search):
    """VCR will record the Tavily API response on first run."""
    result = await tavily_search.search("Python best practices 2025")

    assert "answer" in result
    assert "results" in result
    assert len(result["results"]) > 0
```

**Benefits**:
- No mock setup needed (VCR handles it)
- Real API responses recorded
- Tests use actual data structure
- Deterministic - same result every time
- Fast - no network calls after recording

## Test Coverage

### VCR Tests (8)
- ✓ Basic search with default parameters
- ✓ Basic search depth
- ✓ Advanced search depth
- ✓ Query truncation (400 char limit)
- ✓ Custom max_results parameter
- ✓ Include raw content parameter
- ✓ Include images parameter
- ✓ Exclude answer parameter

### Mock Tests (15)
- ✓ Empty query validation
- ✓ Whitespace query validation
- ✓ Missing API key error
- ✓ 429 rate limit error
- ✓ 500 server error
- ✓ 401 unauthorized error
- ✓ Timeout exception
- ✓ Generic exception
- ✓ Cache hit (Redis)
- ✓ Cache miss and store (Redis)
- ✓ Cache without Redis
- ✓ TavilySearchError re-raised
- ✓ Client close
- ✓ Cache key generation
- ✓ Cache error handling

**Total coverage**: 23 tests (8 VCR + 15 mock)

## CI Integration

### Current Behavior
- `conftest.py` automatically sets `record_mode="none"` when `CI=true`
- Tests fail if cassettes are missing (prevents accidental network calls)
- No API keys needed in CI (cassettes are committed to git)

### CI Requirements
1. Cassettes must be committed to git
2. No `VCR_RECORD_MODE` env var in CI
3. Tests run in replay-only mode

## Next Steps

### 1. Record Cassettes
```bash
cd backend
export TAVILY_API_KEY=your-actual-tavily-key
./scripts/record_vcr_cassettes.sh
```

### 2. Verify Cassettes
```bash
# Check cassettes were created
ls -lh tests/cassettes/unit/tavily_search/

# Verify no API keys leaked
grep -r "tvly-" tests/cassettes/
grep -r "sk-" tests/cassettes/

# Run tests in replay mode (no API key)
poetry run pytest tests/unit/services/tools/test_tavily_search.py -v --vcr-record=none
```

### 3. Commit to Git
```bash
git add tests/cassettes/
git add tests/unit/services/tools/test_tavily_search.py
git add scripts/record_vcr_cassettes.sh
git commit -m "test: convert Tavily tests from mocks to VCR cassettes"
```

## Troubleshooting

### Cassettes Not Created
**Problem**: Tests pass but no cassettes generated
**Solution**: Ensure `@pytest.mark.vcr()` decorator is present

### API Key in Cassette
**Problem**: Security check fails with leaked key
**Solution**:
1. Delete cassettes immediately
2. Verify `vcr_config()` filters the header/param
3. Re-record

### Test Fails on Replay
**Problem**: Test passes during recording but fails on replay
**Solution**: Check that assertions don't depend on dynamic data (timestamps, UUIDs, etc.)

## Documentation

- **[VCR_TESTING_GUIDE.md](./VCR_TESTING_GUIDE.md)**: Complete VCR workflow guide
- **[README.md](./README.md)**: Quick reference
- **[conftest.py](../../conftest.py)**: VCR configuration
- **[test_tavily_search.py](../../unit/services/tools/test_tavily_search.py)**: Example VCR tests

## References

- **pytest-vcr**: https://pytest-vcr.readthedocs.io/
- **VCR.py**: https://vcrpy.readthedocs.io/
- **2025 Best Practices**: Issue #433
