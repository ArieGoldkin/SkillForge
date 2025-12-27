# VCR Testing Guide

This guide explains how to use VCR.py for deterministic HTTP testing with external APIs like Tavily.

## What is VCR?

VCR.py records real HTTP interactions (requests and responses) during the first test run and saves them as "cassettes" (YAML files). Subsequent test runs replay these cassettes instead of making real network calls.

**Benefits:**
- **Deterministic**: Tests produce the same results every time
- **Fast**: No network calls after initial recording
- **No API keys needed**: Once recorded, tests work offline
- **Real responses**: Tests use actual API responses, not mocks

## Quick Start

### 1. Writing VCR Tests

Add the `@pytest.mark.vcr()` decorator to async tests that make HTTP calls:

```python
@pytest.mark.asyncio
@pytest.mark.vcr()
async def test_search_success(tavily_search):
    """VCR will record the Tavily API response on first run."""
    result = await tavily_search.search("Python best practices 2025")

    assert result["query"] == "Python best practices 2025"
    assert "results" in result
    assert len(result["results"]) > 0
```

### 2. Recording New Cassettes

**First-time recording** (requires API key):

```bash
cd backend

# Set API keys in environment
export TAVILY_API_KEY=your-actual-api-key

# Record cassettes
VCR_RECORD_MODE=all pytest tests/unit/services/tools/test_tavily_search.py::test_search_success -v

# Or record all tests at once
VCR_RECORD_MODE=all TAVILY_API_KEY=your-key pytest tests/unit/services/tools/test_tavily_search.py -v
```

**What happens:**
1. VCR makes real API calls
2. Saves requests/responses to `tests/cassettes/unit/tavily_search/test_search_success.yaml`
3. API keys are automatically filtered (replaced with "REDACTED")

### 3. Running Tests with Cassettes

**No API key needed** - tests replay cassettes:

```bash
cd backend

# Run tests normally (uses cassettes)
poetry run pytest tests/unit/services/tools/test_tavily_search.py -v

# Or explicitly specify replay-only mode
poetry run pytest tests/unit/services/tools/test_tavily_search.py -v --vcr-record=none
```

## VCR Record Modes

VCR supports several record modes (set via `VCR_RECORD_MODE` or `--vcr-record`):

| Mode | Behavior | Use Case |
|------|----------|----------|
| `once` (default) | Record if cassette missing, replay if exists | Normal development |
| `none` | Always replay, fail if cassette missing | CI builds, verify cassettes work |
| `all` | Always record, overwrite existing cassettes | Update stale cassettes |
| `new_episodes` | Replay existing, record new interactions | Add new test scenarios |

## Common Workflows

### Update Stale Cassettes

When API responses change or tests are updated:

```bash
# Delete specific cassette
rm tests/cassettes/unit/tavily_search/test_search_success.yaml

# Re-record
VCR_RECORD_MODE=all TAVILY_API_KEY=your-key pytest tests/unit/services/tools/test_tavily_search.py::test_search_success -v

# Or update all cassettes
rm tests/cassettes/unit/tavily_search/*.yaml
VCR_RECORD_MODE=all TAVILY_API_KEY=your-key pytest tests/unit/services/tools/test_tavily_search.py -v
```

### Verify Cassettes in CI

CI automatically uses `record_mode=none` (see `conftest.py`):

```python
@pytest.fixture(scope="module")
def vcr_config():
    # Use "none" mode in CI to fail fast on missing cassettes
    record_mode = "none" if os.environ.get("CI") else "once"
    return {"record_mode": record_mode, ...}
```

This ensures:
- Tests fail if cassettes are missing or incomplete
- No accidental network calls in CI
- Fast, deterministic test runs

### Debug VCR Matching Issues

If tests fail with "Could not find matching cassette":

1. **Check request matching** - VCR matches on `method` and `uri` by default
2. **View cassette** - Open the YAML file to see recorded requests
3. **Re-record** - Delete cassette and record fresh

```bash
# View cassette to debug
cat tests/cassettes/unit/tavily_search/test_search_success.yaml

# Re-record if mismatched
rm tests/cassettes/unit/tavily_search/test_search_success.yaml
VCR_RECORD_MODE=all TAVILY_API_KEY=your-key pytest tests/unit/services/tools/test_tavily_search.py::test_search_success -v
```

## Security: API Key Filtering

VCR automatically filters sensitive data from cassettes:

**Filtered Headers:**
- `authorization`
- `x-api-key`
- `api-key`
- `x-tavily-api-key`

**Filtered Query Parameters:**
- `api_key`
- `token`
- `access_token`

**Configuration** (see `conftest.py`):

```python
@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": [
            ("authorization", "REDACTED"),
            ("x-api-key", "REDACTED"),
        ],
        "filter_query_parameters": [
            ("api_key", "REDACTED"),
        ],
        "before_record_request": redact_api_keys,  # Custom redaction
    }
```

**Always verify** cassettes don't contain real API keys before committing:

```bash
# Search for potential leaks
grep -r "sk-" tests/cassettes/
grep -r "tvly-" tests/cassettes/
```

## Cassette Organization

Cassettes are organized by test module:

```
tests/cassettes/
├── unit/
│   └── tavily_search/
│       ├── test_search_success.yaml
│       ├── test_search_basic_depth.yaml
│       ├── test_search_advanced_depth.yaml
│       └── ...
├── integration/
│   └── ...
└── VCR_TESTING_GUIDE.md (this file)
```

**Naming convention:**
- Directory: `tests/cassettes/unit/<test_module_name>/`
- File: `<test_function_name>.yaml`

## Troubleshooting

### Test fails with "Could not find cassette"

**Cause**: Cassette not recorded yet

**Fix**:
```bash
VCR_RECORD_MODE=all TAVILY_API_KEY=your-key pytest tests/unit/services/tools/test_tavily_search.py::test_name -v
```

### Test fails with "Request does not match cassette"

**Cause**: Test request changed (different URL, headers, or body)

**Fix**: Re-record the cassette
```bash
rm tests/cassettes/unit/tavily_search/test_name.yaml
VCR_RECORD_MODE=all TAVILY_API_KEY=your-key pytest tests/unit/services/tools/test_tavily_search.py::test_name -v
```

### Cassette contains API keys

**Cause**: API key not in filter list

**Fix**:
1. Delete cassette immediately
2. Add header/param to `vcr_config()` in `conftest.py`
3. Re-record

```python
# conftest.py
@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": [
            ("authorization", "REDACTED"),
            ("x-new-api-key-header", "REDACTED"),  # Add here
        ],
    }
```

### VCR not recording despite VCR_RECORD_MODE=all

**Cause**: Test has `@pytest.mark.vcr()` but fixture issues

**Fix**: Check that:
1. Test is marked with `@pytest.mark.vcr()`
2. API key is set in environment
3. Test actually makes HTTP calls (not mocked)

## Best Practices

### 1. Use Realistic Test Data

Use real-world queries that produce meaningful responses:

```python
# Good - realistic query
result = await tavily_search.search("Python best practices 2025")

# Avoid - generic/fake query
result = await tavily_search.search("test query")
```

### 2. Keep Cassettes in Git

Commit cassettes to version control:
- Enables offline testing
- Faster CI builds
- Reproducible tests

### 3. Update Cassettes Regularly

API responses change over time. Update cassettes:
- When API changes
- Quarterly/monthly for long-lived tests
- When test assertions fail

### 4. Separate VCR Tests from Mock Tests

VCR is for integration-style tests with real HTTP. Keep mock-based tests for:
- Error handling (timeout, 429, 500 errors)
- Edge cases (malformed responses)
- Client-side validation (empty query, truncation)

Example structure:
```python
# VCR tests - real API interactions
@pytest.mark.vcr()
async def test_search_success(...):
    """Uses real API response via VCR"""

# Mock tests - error handling
async def test_search_rate_limited(...):
    """Mocks 429 error - VCR not needed"""
    tavily_search.client.post = AsyncMock(side_effect=...)
```

### 5. Document Recording Steps

Add docstrings explaining how to re-record:

```python
@pytest.mark.vcr()
async def test_search_advanced(...):
    """Test advanced search depth.

    To re-record:
        VCR_RECORD_MODE=all TAVILY_API_KEY=key pytest tests/.../test_file.py::test_search_advanced -v
    """
```

## References

- **pytest-vcr**: https://pytest-vcr.readthedocs.io/
- **VCR.py**: https://vcrpy.readthedocs.io/
- **SkillForge VCR setup**: `backend/tests/conftest.py` (lines 708-787)
- **Example tests**: `backend/tests/unit/services/tools/test_tavily_search.py`

---

**Questions?** Check the cassettes README or conftest.py for implementation details.
