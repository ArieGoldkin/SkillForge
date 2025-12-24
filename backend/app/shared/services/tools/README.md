# Tool Services

External API integrations for agent tools.

## Tavily Search

Web search API for Tier 2 validation agents (fact_validator, alternatives_finder).

### Setup

```bash
# Add to .env
TAVILY_API_KEY=your_api_key_here
```

Get your API key from [https://tavily.com](https://tavily.com)

### Usage

```python
from app.shared.services.tools.tavily_search import TavilySearch

# Initialize service
tavily = TavilySearch()

# Basic search (faster, less comprehensive)
results = await tavily.search_basic("LangGraph workflow patterns")

# Advanced search (slower, more comprehensive) - DEFAULT
results = await tavily.search_advanced("FastAPI best practices")

# Custom parameters
results = await tavily.search(
    "PostgreSQL performance tuning",
    search_depth="advanced",
    max_results=10,
    include_answer=True,
    include_raw_content=False,
    include_images=False,
)

# Clean up when done
await tavily.close()
```

### Response Format

```python
{
    "query": str,           # Original search query
    "answer": str,          # AI-generated answer summary
    "results": [
        {
            "title": str,   # Page title
            "url": str,     # Source URL
            "content": str, # Extracted content
            "score": float, # Relevance score (0-1)
        },
        ...
    ],
    "response_time": float, # API response time in seconds
}
```

### Caching

Search results are automatically cached in Redis for 1 hour (3600 seconds).
Cache key includes both query and search depth.

### Error Handling

```python
from app.core.exceptions import TavilySearchError

try:
    results = await tavily.search("test query")
except TavilySearchError as e:
    # Handle search errors
    print(f"Search failed: {e}")
    print(f"Error code: {e.error_code}")
```

### Pricing

- $0.01 per search request
- Caching reduces costs for repeated queries
- Use `search_basic()` for lower latency when appropriate

### Production Considerations

1. **Rate Limiting**: Service handles 429 rate limit responses gracefully
2. **Retries**: Automatic exponential backoff for transient errors (3 attempts)
3. **Timeouts**: 15-second timeout for search requests
4. **Query Length**: Queries longer than 400 characters are automatically truncated
5. **Cache**: Results cached for 1 hour to reduce API costs

### Testing

```bash
# Run tests
poetry run pytest tests/unit/services/tools/test_tavily_search.py -v

# Coverage
poetry run pytest tests/unit/services/tools/test_tavily_search.py --cov=app/shared/services/tools/tavily_search
```
