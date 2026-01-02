---
name: golden-classification
description: Content type and difficulty classification for golden datasets
version: 1.0.0
tags: [golden-dataset, classification, content-type, difficulty]
size: atomic
domain: data-quality
---

# Golden Dataset Classification

## Content Type Classification

| Type | Description | Quality Focus |
|------|-------------|---------------|
| `article` | Technical articles, blog posts | Depth, accuracy, actionability |
| `tutorial` | Step-by-step guides | Completeness, clarity, code quality |
| `research_paper` | Academic papers, whitepapers | Rigor, citations, methodology |
| `documentation` | API docs, reference materials | Accuracy, completeness, examples |
| `video_transcript` | Transcribed video content | Structure, coherence, key points |
| `code_repository` | README, code analysis | Code quality, documentation |

## Classification Logic

```python
def classify_content_type(content: str, source_url: str) -> str:
    """Classify content type based on structure and source."""

    # URL-based hints
    if "arxiv.org" in source_url or "papers" in source_url:
        return "research_paper"
    if "docs." in source_url or "/api/" in source_url:
        return "documentation"
    if "github.com" in source_url:
        return "code_repository"

    # Content-based analysis
    if has_step_by_step_structure(content):
        return "tutorial"
    if has_academic_structure(content):  # Abstract, methodology, results
        return "research_paper"

    return "article"
```

## Difficulty Stratification

| Level | Semantic Complexity | Expected Score | Characteristics |
|-------|---------------------|----------------|-----------------|
| **trivial** | Direct keyword match | >0.85 | Technical terms, exact phrases |
| **easy** | Common synonyms | >0.70 | Well-known concepts |
| **medium** | Paraphrased intent | >0.55 | Conceptual, multi-topic |
| **hard** | Multi-hop reasoning | >0.40 | Cross-domain, comparative |
| **adversarial** | Edge cases | Graceful fail | Robustness tests |

## Difficulty Classification

```python
def classify_difficulty(document: dict) -> str:
    """Classify document difficulty for retrieval testing."""

    factors = {
        "technical_density": count_technical_terms(document["content"]),
        "section_count": len(document.get("sections", [])),
        "cross_references": count_cross_references(document),
        "abstraction_level": assess_abstraction(document),
    }

    # Scoring rubric
    score = 0
    if factors["technical_density"] > 50:
        score += 2
    if factors["section_count"] > 10:
        score += 1
    if factors["cross_references"] > 5:
        score += 2
    if factors["abstraction_level"] == "high":
        score += 2

    # Map score to difficulty
    if score <= 2:
        return "trivial"
    elif score <= 4:
        return "easy"
    elif score <= 6:
        return "medium"
    elif score <= 8:
        return "hard"
    else:
        return "adversarial"
```

## Best Practices

- **Use URL hints first** - Most reliable signal
- **Balance difficulty levels** - Need trivial AND hard queries
- **Content type coverage** - Don't over-index on articles
