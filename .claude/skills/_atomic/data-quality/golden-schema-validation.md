---
name: golden-schema-validation
description: Schema validation and integrity rules for golden datasets
version: 1.0.0
tags: [golden-dataset, schema, validation, integrity]
size: atomic
domain: data-quality
---

# Golden Dataset Schema Validation

## Document Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "title", "source_url", "content_type", "sections"],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^[a-z0-9-]+$"
    },
    "title": {
      "type": "string",
      "minLength": 10,
      "maxLength": 200
    },
    "source_url": {
      "type": "string",
      "format": "uri"
    },
    "content_type": {
      "enum": ["article", "tutorial", "research_paper", "documentation", "video_transcript", "code_repository"]
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"},
      "minItems": 2,
      "maxItems": 10
    },
    "sections": {
      "type": "array",
      "minItems": 1,
      "items": {
        "required": ["id", "title", "content"],
        "properties": {
          "id": {"type": "string"},
          "title": {"type": "string"},
          "content": {"type": "string", "minLength": 50}
        }
      }
    }
  }
}
```

## URL Contract

Golden dataset URLs MUST be real canonical URLs, not placeholders.

```python
FORBIDDEN_URL_PATTERNS = [
    "skillforge.dev",
    "placeholder",
    "example.com",
    "localhost",
    "127.0.0.1",
]

def validate_url(url: str) -> tuple[bool, str]:
    """Validate URL is not a placeholder."""
    for pattern in FORBIDDEN_URL_PATTERNS:
        if pattern in url.lower():
            return False, f"URL contains forbidden pattern: {pattern}"

    if not url.startswith("https://"):
        if not url.startswith("http://arxiv.org"):
            return False, "URL must use HTTPS"

    return True, "OK"
```

## Integrity Rules

### Unique IDs

```python
def validate_unique_ids(documents: list, queries: list) -> list[str]:
    """Ensure all IDs are unique."""
    errors = []

    doc_ids = [d["id"] for d in documents]
    if len(doc_ids) != len(set(doc_ids)):
        duplicates = [id for id in doc_ids if doc_ids.count(id) > 1]
        errors.append(f"Duplicate document IDs: {set(duplicates)}")

    query_ids = [q["id"] for q in queries]
    if len(query_ids) != len(set(query_ids)):
        duplicates = [id for id in query_ids if query_ids.count(id) > 1]
        errors.append(f"Duplicate query IDs: {set(duplicates)}")

    return errors
```

### Referential Integrity

```python
def validate_references(documents: list, queries: list) -> list[str]:
    """Ensure query expected_chunks reference valid sections."""
    errors = []

    valid_sections = set()
    for doc in documents:
        for section in doc.get("sections", []):
            valid_sections.add(section["id"])

    for query in queries:
        for chunk_id in query.get("expected_chunks", []):
            if chunk_id not in valid_sections:
                errors.append(
                    f"Query {query['id']} references invalid section: {chunk_id}"
                )

    return errors
```

### Content Quality

```python
def validate_content_quality(document: dict) -> list[str]:
    """Validate document meets quality standards."""
    warnings = []

    title = document.get("title", "")
    if len(title) < 10:
        warnings.append("Title too short (min 10 chars)")

    for section in document.get("sections", []):
        content = section.get("content", "")
        if len(content) < 50:
            warnings.append(f"Section {section['id']} content too short")

    tags = document.get("tags", [])
    if len(tags) < 2:
        warnings.append("Too few tags (min 2)")

    return warnings
```

## Full Validation

```python
async def validate_full_dataset() -> dict:
    """Run comprehensive validation."""
    documents = load_documents()
    queries = load_queries()

    errors = []
    warnings = []

    # Schema validation
    for doc in documents:
        errors.extend(validate_schema(doc))

    # Unique IDs
    errors.extend(validate_unique_ids(documents, queries))

    # Referential integrity
    errors.extend(validate_references(documents, queries))

    # URL validation
    for doc in documents:
        valid, msg = validate_url(doc.get("source_url", ""))
        if not valid:
            errors.append(f"[{doc['id']}] {msg}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }
```
