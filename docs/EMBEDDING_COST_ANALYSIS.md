# Embedding Service Cost Analysis

**Date:** November 25, 2025  
**Status:** ✅ Migration Completed  
**Current Setup:** OpenAI (text-embedding-3-small) - $0.02 per million tokens  
**Previous:** Ollama (nomic-embed-text) - Free, Local (migrated from)

## Current Setup

### Ollama (nomic-embed-text)
- **Cost:** $0 (free, runs locally)
- **Dimensions:** 768
- **Model Size:** ~137M parameters
- **Text Limit:** 8,000 characters (truncated in code)
- **Latency:** Variable (depends on local hardware)
- **Reliability:** Can have connection issues (as seen in tests)

### Configuration
```python
# backend/app/core/config.py
OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
EMBEDDING_DIMENSIONS: int = 768
MAX_TEXT_LENGTH: int = 8000  # Characters truncated
```

## OpenAI Embedding Options

### text-embedding-3-small
- **Cost:** $0.02 per million tokens
- **Dimensions:** 1536 (or configurable: 512, 1024, 1536)
- **Text Limit:** 8,191 tokens (~32,000 characters)
- **Latency:** ~50-200ms (API call)
- **Reliability:** High (managed service)

### text-embedding-3-large
- **Cost:** $0.13 per million tokens (6.5x more expensive)
- **Dimensions:** 3072
- **Text Limit:** 8,191 tokens
- **Latency:** ~100-300ms
- **Reliability:** High

## Cost Calculation

### Assumptions
Based on your workflow:
- Average article: ~24,000 characters (like Claude Opus 4.5 article)
- Text truncated to 8,000 characters for embeddings
- ~1 token = 4 characters (rough estimate)
- 8,000 characters ≈ 2,000 tokens per embedding

### Monthly Cost Estimates

#### Scenario 1: Light Usage (100 analyses/month)
- Embeddings per month: 100
- Tokens per embedding: ~2,000
- Total tokens: 200,000
- **Cost: $0.004** (less than 1 cent)

#### Scenario 2: Moderate Usage (1,000 analyses/month)
- Embeddings per month: 1,000
- Tokens per embedding: ~2,000
- Total tokens: 2,000,000
- **Cost: $0.04** (4 cents)

#### Scenario 3: Heavy Usage (10,000 analyses/month)
- Embeddings per month: 10,000
- Tokens per embedding: ~2,000
- Total tokens: 20,000,000
- **Cost: $0.40** (40 cents)

#### Scenario 4: Enterprise (100,000 analyses/month)
- Embeddings per month: 100,000
- Tokens per embedding: ~2,000
- Total tokens: 200,000,000
- **Cost: $4.00**

### Batch Processing Discount
If you batch multiple embeddings:
- **text-embedding-3-small:** $0.01 per million tokens (50% discount)
- **text-embedding-3-large:** $0.065 per million tokens (50% discount)

## Cost Comparison Table

| Usage Level | Analyses/Month | Ollama Cost | OpenAI Cost (small) | OpenAI Cost (large) | Savings vs Large |
|-------------|---------------|-------------|---------------------|---------------------|------------------|
| Light       | 100           | $0.00       | $0.004              | $0.026              | 85%              |
| Moderate    | 1,000         | $0.00       | $0.04               | $0.26               | 85%              |
| Heavy       | 10,000        | $0.00       | $0.40               | $2.60               | 85%              |
| Enterprise  | 100,000       | $0.00       | $4.00               | $26.00              | 85%              |

## Implementation Considerations

### 1. Dimension Change (768 → 1536)
**Current:** 768 dimensions (nomic-embed-text)  
**OpenAI:** 1536 dimensions (text-embedding-3-small)

**Impact:**
- Database migration required (Vector(768) → Vector(1536))
- Existing embeddings become invalid
- Re-embedding all existing content needed
- 2x storage per embedding

**Migration Path:**
```sql
-- 1. Add new column
ALTER TABLE analyses ADD COLUMN content_embedding_new vector(1536);

-- 2. Re-embed all content (one-time cost)
-- 3. Swap columns
ALTER TABLE analyses DROP COLUMN content_embedding;
ALTER TABLE analyses RENAME COLUMN content_embedding_new TO content_embedding;
```

### 2. Code Changes Required

**Minimal changes needed:**
```python
# backend/app/services/embeddings.py
# Replace Ollama client with OpenAI client
from openai import AsyncOpenAI

class EmbeddingService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "text-embedding-3-small"
        self.dimensions = 1536  # or 512, 1024, 1536
```

### 3. Configuration Updates

```python
# backend/app/core/config.py
EMBEDDING_PROVIDER: str = "openai"  # or "ollama"
EMBEDDING_MODEL: str = "text-embedding-3-small"
EMBEDDING_DIMENSIONS: int = 1536  # Changed from 768
```

## Benefits of Switching

### Advantages
1. **Reliability:** No connection issues, managed service
2. **Performance:** Consistent latency, no local resource usage
3. **Scalability:** No hardware constraints
4. **Quality:** OpenAI embeddings often perform better in benchmarks
5. **Consistency:** Same provider as LLM (simpler infrastructure)

### Disadvantages
1. **Cost:** $0.02 per million tokens (vs $0 free)
2. **Latency:** Network call vs local (but more reliable)
3. **Dependency:** Requires internet, API key management
4. **Migration:** One-time cost to re-embed existing content

## Recommendation

### For Development/Testing
**Keep Ollama** - Free, no API costs, works offline

### For Production
**Switch to OpenAI** if:
- You're processing >1,000 analyses/month (costs are minimal)
- Reliability is critical (no connection issues)
- You want consistent performance
- You're already using OpenAI for LLM (simplifies infrastructure)

**Cost is negligible** even at scale:
- 10,000 analyses/month = $0.40
- 100,000 analyses/month = $4.00

### Hybrid Approach
Consider supporting both:
- Development: Use Ollama (free, local)
- Production: Use OpenAI (reliable, low cost)
- Configuration-driven switching

## Implementation Cost Estimate

### One-Time Migration
1. **Code changes:** ~2-4 hours
2. **Database migration:** ~1 hour
3. **Re-embedding existing content:** Depends on volume
   - 1,000 existing analyses: ~$0.02
   - 10,000 existing analyses: ~$0.20

### Ongoing Costs
- **Per embedding:** ~$0.00004 (0.004 cents)
- **Per 1,000 analyses:** ~$0.04
- **Per 10,000 analyses:** ~$0.40

## Conclusion

**OpenAI embeddings are extremely cost-effective:**
- Even at 100,000 analyses/month, cost is only $4.00
- Reliability benefits far outweigh minimal costs
- Since you're already using OpenAI for LLM, infrastructure is simpler
- **Recommendation: Switch to OpenAI for production**

The cost is so low that it's essentially "free" compared to:
- Infrastructure costs (servers, maintenance)
- Developer time (debugging Ollama connection issues)
- Reliability issues (failed embeddings)

**Bottom line:** At $0.40/month for 10,000 analyses, the cost is negligible compared to the reliability and performance benefits.
