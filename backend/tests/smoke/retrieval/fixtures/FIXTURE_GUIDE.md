# Retrieval Fixtures Guide

This guide documents the test fixtures used for retrieval smoke tests, including query difficulty stratification criteria.

## Difficulty Stratification Criteria

All evaluation queries are labeled with difficulty levels that indicate expected retrieval performance thresholds.

| Level | Criteria | Expected Similarity | Example |
|-------|----------|---------------------|---------|
| **Trivial** | Exact keyword match, technical terms | >0.85 | "JWT", "OAuth2 password flow" |
| **Easy** | Common synonyms, slight variations | >0.70 | "secure web API methods" |
| **Medium** | Paraphrased intent, conceptual queries | >0.55 | "making queries faster" |
| **Hard** | Multi-hop reasoning, cross-domain | >0.40 | "compare React hooks to Vue composition" |
| **Adversarial** | Edge cases, robustness tests | Graceful degradation | Injection, misspellings, off-domain |

### Detailed Criteria

#### Trivial (Expected: >85% similarity)
- Direct keyword match with indexed content
- Technical acronyms and standard terms
- No semantic inference required
- Example: "asyncio event loop" matches async programming docs exactly

#### Easy (Expected: >70% similarity)
- Queries using common synonyms
- Minor paraphrasing of concepts
- Well-known technology combinations
- Example: "secure web API authentication" matches OAuth2/JWT content

#### Medium (Expected: >55% similarity)
- Intent-based queries requiring semantic understanding
- Cross-section relevance (multiple topics)
- Conceptual questions about implementation
- Example: "making database queries run faster" matches SQL optimization

#### Hard (Expected: >40% similarity)
- Multi-hop reasoning required
- Fine-grained matching within larger sections
- Cross-domain or comparative queries
- Example: "How does ReAct reasoning and acting loop work"

#### Adversarial (Expected: Graceful degradation)
- Off-domain content (should return low scores)
- Edge cases like very short queries or special characters
- Tests system robustness, not accuracy
- Example: "quantum computing algorithms" (unrelated domain)

## Query Categories

| Category | Purpose | Typical Difficulty |
|----------|---------|-------------------|
| **specific** | Direct technology lookup | trivial, easy, medium |
| **broad** | Multi-section retrieval | medium |
| **negative** | Off-domain, should NOT match | adversarial |
| **edge** | Robustness tests | adversarial |
| **coarse-to-fine** | Hierarchical retrieval | medium, hard |

## Distribution Requirements

For evaluation datasets to be comprehensive, maintain minimum coverage:

- **Minimum 3 queries per difficulty level**
- **At least 5 queries for medium difficulty** (most common real-world case)
- **Balance specific vs broad categories**

### Current Distribution (queries.json)

| Difficulty | Count | Queries |
|------------|-------|---------|
| Trivial | 3 | q-oauth2-impl, q-async-await, q-sql-join |
| Easy | 5 | q-jwt-expiry, q-react-state, q-langchain-tools, q-sem-synonym, q-k8s-scaling |
| Medium | 6 | q-api-security-broad, q-deployment-broad, q-sem-paraphrase, q-vector-search, q-c2f-tools-coarse, q-c2f-react-coarse |
| Hard | 3 | q-c2f-tools-fine, q-c2f-react-fine, q-c2f-intro-hierarchy |
| Adversarial | 4 | q-neg-quantum, q-neg-rust, q-edge-short, q-edge-special |
| **Total** | **21** | |

## File Structure

```
tests/smoke/retrieval/fixtures/
├── queries.json          # Test queries with expected chunks and difficulty
├── chunks.json           # Indexed content chunks for testing
├── sample_corpus.json    # Sample documents for full indexing tests
└── FIXTURE_GUIDE.md      # This documentation file
```

## Adding New Queries

When adding new test queries:

1. **Assign difficulty level** based on criteria above
2. **Define expected_chunks** with precise chunk IDs
3. **Set appropriate score thresholds** matching difficulty
4. **Add to appropriate category** (specific, broad, negative, edge, coarse-to-fine)
5. **Verify distribution** maintains minimum coverage

Example query structure:
```json
{
  "id": "q-example-query",
  "query": "How to implement feature X",
  "modes": ["semantic", "hybrid"],
  "category": "specific",
  "difficulty": "easy",
  "expected_chunks": ["section/subsection"],
  "min_score": 0.7,
  "max_score": null,
  "description": "Description of what this tests"
}
```
