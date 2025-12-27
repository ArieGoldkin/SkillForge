# VCR Cassettes

This directory contains recorded HTTP responses for deterministic testing.

## Recording New Cassettes

```bash
# Set API keys in environment
export TAVILY_API_KEY=your-key
export JINA_API_KEY=your-key

# Record all cassettes (or specific test)
VCR_RECORD_MODE=all pytest tests/unit/services/external/ -v

# Or record specific test
VCR_RECORD_MODE=all pytest tests/unit/services/external/test_tavily.py::test_search -v
```

## Refreshing Stale Cassettes

```bash
# Delete specific cassette
rm tests/cassettes/unit/tavily_search/test_search_success.yaml

# Re-record
VCR_RECORD_MODE=all pytest tests/unit/services/external/test_tavily.py::test_search_success -v
```

## CI Behavior

In CI (`CI=true`), cassettes are read-only. Tests fail if cassette is missing.

## Security

API keys are automatically filtered. Never commit real secrets.
