---
name: golden-quality-dimensions
description: Quality evaluation dimensions for golden dataset curation
version: 1.0.0
tags: [golden-dataset, quality, evaluation, scoring]
size: atomic
domain: data-quality
---

# Golden Dataset Quality Dimensions

## Four Dimensions

### 1. Accuracy (Weight: 0.25)

**What it measures:** Factual correctness, up-to-date information

**Criteria:**
- Technical claims are verifiable
- Code examples are syntactically correct
- No outdated information
- Sources/citations where applicable

**Thresholds:**
- Perfect: 0.95-1.0 (all claims verifiable)
- Acceptable: 0.70-0.94 (minor inaccuracies)
- Failing: <0.70 (significant errors)

### 2. Coherence (Weight: 0.20)

**What it measures:** Logical flow, structure, readability

**Criteria:**
- Clear introduction and conclusion
- Logical section ordering
- Smooth transitions
- Consistent terminology

**Thresholds:**
- Perfect: 0.90-1.0 (professional quality)
- Acceptable: 0.60-0.89 (readable but rough)
- Failing: <0.60 (confusing structure)

### 3. Depth (Weight: 0.25)

**What it measures:** Thoroughness, detail level

**Criteria:**
- Comprehensive coverage
- Edge cases mentioned
- Context and background
- Appropriate detail for audience

**Thresholds:**
- Perfect: 0.90-1.0 (exhaustive)
- Acceptable: 0.55-0.89 (covers main points)
- Failing: <0.55 (superficial)

### 4. Relevance (Weight: 0.30)

**What it measures:** Alignment with target domains

**Target domains:**
- AI/ML (LangGraph, RAG, agents, embeddings)
- Backend (FastAPI, PostgreSQL, APIs)
- Frontend (React, TypeScript)
- DevOps (Docker, Kubernetes, CI/CD)
- Security (OWASP, authentication)

**Thresholds:**
- Perfect: 0.95-1.0 (core domain)
- Acceptable: 0.70-0.94 (related domain)
- Failing: <0.70 (off-topic)

## Weighted Score Calculation

```python
def calculate_quality_score(scores: dict) -> float:
    """Calculate weighted quality score."""
    return (
        scores["accuracy"] * 0.25 +
        scores["coherence"] * 0.20 +
        scores["depth"] * 0.25 +
        scores["relevance"] * 0.30
    )

def make_decision(quality_score: float, confidence: float) -> str:
    """Decide include/review/exclude based on scores."""
    if quality_score >= 0.75 and confidence >= 0.7:
        return "include"
    elif quality_score >= 0.55:
        return "review"
    else:
        return "exclude"
```

## Evaluation Output Schema

```json
{
    "accuracy": {"score": 0.85, "rationale": "..."},
    "coherence": {"score": 0.90, "rationale": "..."},
    "depth": {"score": 0.75, "rationale": "..."},
    "relevance": {"score": 0.95, "rationale": "..."},
    "weighted_total": 0.87,
    "recommendation": "include"
}
```

## Quality Thresholds

```yaml
minimum_quality_score: 0.70
minimum_confidence: 0.65
required_tags: 2
required_queries: 3
```
