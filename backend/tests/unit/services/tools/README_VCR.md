# Tavily Search VCR Tests

This test file uses **VCR.py** for deterministic HTTP testing.

## Overview

**8 tests use VCR** (record real API responses):
- `test_search_success` - Basic search
- `test_search_basic_depth` - Basic depth parameter
- `test_search_advanced_depth` - Advanced depth parameter
- `test_search_query_truncation` - Long query truncation
- `test_search_custom_max_results` - Custom max_results
- `test_search_include_raw_content` - Raw content parameter
- `test_search_include_images` - Images parameter
- `test_search_no_answer` - Exclude answer parameter

**15 tests use mocks** (error handling, validation):
- Error tests: rate limit, server error, timeout, exceptions
- Cache tests: Redis integration, cache hits/misses
- Validation tests: empty query, missing API key

## Quick Commands

### Run all tests (uses cassettes, no API key needed)
```bash
cd backend
poetry run pytest tests/unit/services/tools/test_tavily_search.py -v
```

### Record new cassettes (requires API key)
```bash
cd backend
export TAVILY_API_KEY=your-actual-key
./scripts/record_vcr_cassettes.sh
```

### Run specific VCR test
```bash
poetry run pytest tests/unit/services/tools/test_tavily_search.py::test_search_success -v
```

### Update specific cassette
```bash
rm tests/cassettes/unit/tavily_search/test_search_success.yaml
VCR_RECORD_MODE=all TAVILY_API_KEY=your-key pytest tests/unit/services/tools/test_tavily_search.py::test_search_success -v
```

## Cassette Location

Cassettes are stored in:
```
tests/cassettes/unit/tavily_search/
├── test_search_success.yaml
├── test_search_basic_depth.yaml
├── test_search_advanced_depth.yaml
├── test_search_query_truncation.yaml
├── test_search_custom_max_results.yaml
├── test_search_include_raw_content.yaml
├── test_search_include_images.yaml
└── test_search_no_answer.yaml
```

## How VCR Works

1. **First run** (with `VCR_RECORD_MODE=all`):
   - Makes real API call to Tavily
   - Records request + response to YAML file
   - API keys are automatically filtered

2. **Subsequent runs**:
   - Replays recorded response from cassette
   - No network call needed
   - Fast, deterministic tests

## Security

API keys are **automatically filtered** from cassettes:
- `authorization` header → "REDACTED"
- `x-api-key` header → "REDACTED"
- `x-tavily-api-key` header → "REDACTED"
- `api_key` query param → "REDACTED"

**Always verify** before committing:
```bash
grep -r "tvly-" tests/cassettes/
```

## CI/CD

In CI (`CI=true`), VCR uses `record_mode="none"`:
- Tests fail if cassettes are missing
- No network calls in CI
- Fast, deterministic builds

## Full Documentation

See:
- `tests/cassettes/VCR_TESTING_GUIDE.md` - Complete VCR workflow
- `tests/cassettes/CONVERSION_SUMMARY.md` - Conversion details
- `tests/cassettes/README.md` - Quick reference
- `scripts/record_vcr_cassettes.sh` - Recording script

## Troubleshooting

**Missing cassette error?**
```bash
# Record the cassette
VCR_RECORD_MODE=all TAVILY_API_KEY=your-key pytest tests/unit/services/tools/test_tavily_search.py::test_name -v
```

**Test fails on replay?**
```bash
# Re-record cassette
rm tests/cassettes/unit/tavily_search/test_name.yaml
VCR_RECORD_MODE=all TAVILY_API_KEY=your-key pytest tests/unit/services/tools/test_tavily_search.py::test_name -v
```

**API key in cassette?**
```bash
# Delete immediately and fix filter in conftest.py
rm tests/cassettes/unit/tavily_search/*.yaml
```
