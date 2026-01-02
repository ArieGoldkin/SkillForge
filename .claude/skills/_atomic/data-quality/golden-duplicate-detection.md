---
name: golden-duplicate-detection
description: URL and semantic duplicate detection for golden datasets
version: 1.0.0
tags: [golden-dataset, duplicates, semantic, similarity]
size: atomic
domain: data-quality
---

# Golden Dataset Duplicate Detection

## URL Duplicate Check

```python
def check_url_duplicate(
    new_url: str,
    source_url_map: dict[str, str],
) -> str | None:
    """Check if URL already exists in dataset.

    Returns document ID if duplicate found.
    """
    normalized = normalize_url(new_url)

    for doc_id, existing_url in source_url_map.items():
        if normalize_url(existing_url) == normalized:
            return doc_id

    return None

def normalize_url(url: str) -> str:
    """Normalize URL for comparison."""
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(url.lower())

    # Remove www prefix, trailing slashes
    netloc = parsed.netloc.replace("www.", "")
    path = parsed.path.rstrip("/")

    return urlunparse((
        parsed.scheme,
        netloc,
        path,
        "", "", ""  # No params, query, fragment
    ))
```

## Semantic Similarity Check

```python
import numpy as np

async def check_semantic_duplicate(
    new_content: str,
    existing_embeddings: list[tuple[str, np.ndarray]],
    embedding_service,
    threshold: float = 0.85,
) -> tuple[str, float] | None:
    """Check if content is semantically duplicate.

    Args:
        new_content: Content to check
        existing_embeddings: List of (doc_id, embedding) tuples
        threshold: Similarity threshold (0.85 = 85% similar)

    Returns:
        (doc_id, similarity) if duplicate found, None otherwise
    """
    # Generate embedding
    new_embedding = await embedding_service.generate_embedding(
        text=new_content[:8000],
        normalize=True,
    )
    new_vec = np.array(new_embedding)

    # Compare against existing
    max_similarity = 0.0
    most_similar_doc = None

    for doc_id, existing_vec in existing_embeddings:
        similarity = np.dot(new_vec, existing_vec)  # Cosine (normalized)

        if similarity > max_similarity:
            max_similarity = similarity
            most_similar_doc = doc_id

    if max_similarity >= threshold:
        return (most_similar_doc, max_similarity)

    return None
```

## Combined Validation

```python
async def validate_for_duplicates(
    document: dict,
    source_url_map: dict[str, str],
    existing_embeddings: list,
    embedding_service,
) -> dict:
    """Check both URL and semantic duplicates."""

    errors = []
    warnings = []

    # URL check
    url_dup = check_url_duplicate(document["source_url"], source_url_map)
    if url_dup:
        errors.append(f"URL already exists as: {url_dup}")

    # Semantic check
    content = " ".join(s["content"] for s in document.get("sections", []))
    semantic_dup = await check_semantic_duplicate(
        content, existing_embeddings, embedding_service
    )

    if semantic_dup:
        doc_id, similarity = semantic_dup
        if similarity >= 0.90:
            errors.append(
                f"Content too similar to {doc_id} ({similarity:.0%})"
            )
        elif similarity >= 0.80:
            warnings.append(
                f"Content similar to {doc_id} ({similarity:.0%})"
            )

    return {
        "has_duplicates": len(errors) > 0,
        "errors": errors,
        "warnings": warnings,
    }
```

## Thresholds

| Similarity | Action |
|------------|--------|
| ≥90% | **Block** - Too similar, likely duplicate |
| 80-89% | **Warn** - Review manually |
| <80% | **OK** - Sufficiently different |

## Best Practices

- **Check URL first** - Fast and definitive
- **Semantic check on content** - Catches rephrased duplicates
- **Truncate for embedding** - Use first 8k chars
- **Normalize URLs** - Remove www, trailing slashes
