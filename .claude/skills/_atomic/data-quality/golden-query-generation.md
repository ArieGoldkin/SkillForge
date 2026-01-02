---
name: golden-query-generation
description: Test query generation for golden dataset evaluation
version: 1.0.0
tags: [golden-dataset, queries, testing, retrieval]
size: atomic
domain: data-quality
---

# Golden Dataset Query Generation

## Query Requirements

For each document, generate 3-5 test queries:
- At least 1 TRIVIAL query (exact keyword match)
- At least 1 EASY query (synonyms, common terms)
- At least 1 MEDIUM query (paraphrased intent)
- Optional: 1 HARD query (cross-section reasoning)

## Query Schema

```json
{
    "id": "q-doc-id-001",
    "query": "How to implement X with Y?",
    "difficulty": "medium",
    "expected_chunks": ["section-id-1", "section-id-2"],
    "min_score": 0.55,
    "modes": ["semantic", "hybrid"],
    "category": "specific",
    "description": "Tests retrieval of X implementation"
}
```

## Query Categories

| Category | Description | Example |
|----------|-------------|---------|
| `specific` | Targets specific section | "How to configure HNSW index?" |
| `broad` | Spans multiple sections | "Explain vector search" |
| `negative` | Should NOT match | "Does this cover MongoDB?" |
| `edge` | Edge cases, robustness | "What about empty vectors?" |
| `coarse-to-fine` | General → specific | "Database indexing strategies" |

## Generation Prompt

```python
Task(
    subagent_type="Explore",
    prompt="""TEST QUERY GENERATION

    Document ID: {document_id}
    Title: {title}
    Sections: {section_titles}
    Content preview: {content_preview}

    Generate 3-5 test queries with varied difficulty:

    1. At least 1 TRIVIAL query (exact keyword match)
    2. At least 1 EASY query (synonyms, common terms)
    3. At least 1 MEDIUM query (paraphrased intent)
    4. Optional: 1 HARD query (cross-section reasoning)

    For each query specify:
    - Query text
    - Expected sections to match
    - Difficulty level
    - Minimum expected score

    Output JSON:
    {
        "queries": [
            {
                "id": "q-{doc-id}-{num}",
                "query": "...",
                "difficulty": "medium",
                "expected_chunks": ["section-id-1"],
                "min_score": 0.55,
                "modes": ["semantic", "hybrid"],
                "category": "specific",
                "description": "..."
            }
        ]
    }
    """
)
```

## Difficulty-to-Score Mapping

```python
DIFFICULTY_THRESHOLDS = {
    "trivial": 0.85,
    "easy": 0.70,
    "medium": 0.55,
    "hard": 0.40,
    "adversarial": 0.20,
}
```

## Best Practices

- **Vary query phrasing** - Don't just copy section titles
- **Include edge cases** - Typos, abbreviations, synonyms
- **Cross-section queries** - Test multi-hop reasoning
- **Negative queries** - Verify no false positives
