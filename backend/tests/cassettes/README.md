# VCR Cassettes

This directory contains recorded HTTP responses for deterministic testing.

## Quick Start

### Record new cassettes (first time)
```bash
cd backend
export TAVILY_API_KEY=your-key
VCR_RECORD_MODE=all pytest tests/unit/services/tools/test_tavily_search.py -v
```

### Run tests with cassettes (no API key needed)
```bash
cd backend
poetry run pytest tests/unit/services/tools/test_tavily_search.py -v
```

### Update stale cassettes
```bash
# Delete specific cassette
rm tests/cassettes/unit/tavily_search/test_search_success.yaml

# Re-record
VCR_RECORD_MODE=all TAVILY_API_KEY=your-key pytest tests/unit/services/tools/test_tavily_search.py::test_search_success -v
```

## Full Documentation

See **[VCR_TESTING_GUIDE.md](./VCR_TESTING_GUIDE.md)** for:
- Complete workflow examples
- Security best practices
- Troubleshooting guide
- CI/CD integration
- Cassette organization

## Security

API keys are automatically filtered from cassettes:
- `authorization`, `x-api-key`, `api-key` headers → "REDACTED"
- `api_key`, `token` query params → "REDACTED"

Always verify before committing:
```bash
grep -r "sk-" tests/cassettes/
grep -r "tvly-" tests/cassettes/
```

## CI Behavior

In CI (`CI=true`), record mode is `none` - tests fail if cassettes are missing or incomplete.
