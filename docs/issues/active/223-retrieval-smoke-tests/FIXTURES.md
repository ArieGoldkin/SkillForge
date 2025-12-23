# Smoke Test Fixtures Design

## Overview

This document defines the test fixtures for the retrieval smoke test suite. Fixtures are designed to be:

1. **Representative** - Cover different content types and document lengths
2. **Deterministic** - Same queries always produce same expected results
3. **Minimal** - Small enough for fast CI execution
4. **Comprehensive** - Cover all search modes and edge cases

## Document Fixtures

### Structure

```json
{
  "version": "1.0",
  "documents": [
    {
      "id": "string (unique identifier)",
      "title": "string",
      "content_type": "article | tutorial | api_docs | repo",
      "bucket": "short | long",
      "language": "en",
      "tags": ["string"],
      "sections": [
        {
          "id": "string (doc_id/section_slug)",
          "title": "string",
          "content": "string (full text)",
          "granularity": "coarse"
        }
      ]
    }
  ]
}
```

### Proposed Documents (8 total)

#### Short Documents (< 2000 tokens)

| ID | Title | Type | Sections | Purpose |
|----|-------|------|----------|---------|
| `fastapi-auth` | FastAPI Authentication | article | 3 | OAuth2, security, specific terms |
| `python-async` | Python Async Basics | tutorial | 3 | Async/await, common patterns |
| `react-hooks` | React Hooks Guide | article | 3 | Frontend, JavaScript concepts |
| `sql-basics` | SQL Query Fundamentals | tutorial | 3 | Database, query patterns |

#### Long Documents (> 4000 tokens)

| ID | Title | Type | Sections | Purpose |
|----|-------|------|----------|---------|
| `langchain-agents` | LangChain Agent Development | tutorial | 8 | AI/ML, agents, multi-section |
| `kubernetes-deploy` | Kubernetes Deployment | article | 6 | DevOps, infrastructure |
| `graphql-api` | GraphQL API Design | api_docs | 7 | API design, schemas |
| `ml-pipeline` | ML Pipeline Architecture | article | 6 | Data science, pipelines |

### Sample Document Content

```json
{
  "id": "fastapi-auth",
  "title": "FastAPI Authentication Guide",
  "content_type": "article",
  "bucket": "short",
  "language": "en",
  "tags": ["fastapi", "python", "authentication", "oauth2"],
  "sections": [
    {
      "id": "fastapi-auth/intro",
      "title": "Introduction to FastAPI Security",
      "content": "FastAPI provides built-in security utilities that make implementing " +
        "authentication straightforward. The framework includes OAuth2 with Password flow, " +
        "JWT tokens, and API key authentication out of the box. This guide covers the " +
        "essential patterns for securing your FastAPI applications.",
      "granularity": "coarse"
    },
    {
      "id": "fastapi-auth/oauth2-password",
      "title": "OAuth2 with Password Flow",
      "content": "The OAuth2 password flow is ideal for first-party applications where you " +
        "control both the client and the server. To implement it, first create a token " +
        "endpoint that validates credentials and returns a JWT. Use the OAuth2PasswordBearer " +
        "class to define the token URL. The password flow exchanges username and password " +
        "for an access token, which is then used for subsequent API requests.",
      "granularity": "coarse"
    },
    {
      "id": "fastapi-auth/jwt-tokens",
      "title": "JWT Token Management",
      "content": "JSON Web Tokens (JWT) are the standard for stateless authentication in FastAPI. " +
        "Create tokens using the python-jose library with HS256 or RS256 algorithms. " +
        "Include user claims like user_id, email, and roles. Set appropriate expiration " +
        "times - typically 15 minutes for access tokens and 7 days for refresh tokens. " +
        "Always validate tokens on protected endpoints using FastAPI's dependency injection.",
      "granularity": "coarse"
    }
  ]
}
```

## Query Fixtures

### Structure

```json
{
  "version": "1.0",
  "queries": [
    {
      "id": "string (unique identifier)",
      "query": "string (search query)",
      "modes": ["semantic", "keyword", "hybrid"],
      "category": "specific | broad | negative | edge",
      "expected_chunks": ["doc_id/section_id", ...],
      "min_score": 0.7,
      "description": "string (test purpose)"
    }
  ]
}
```

### Query Categories

#### 1. Specific Queries (Should find exact content)

```json
[
  {
    "id": "q-oauth2-impl",
    "query": "How to implement OAuth2 password flow in FastAPI?",
    "modes": ["semantic", "keyword", "hybrid"],
    "category": "specific",
    "expected_chunks": ["fastapi-auth/oauth2-password"],
    "min_score": 0.7,
    "description": "Direct match for OAuth2 implementation"
  },
  {
    "id": "q-jwt-expiry",
    "query": "JWT token expiration time best practices",
    "modes": ["semantic", "hybrid"],
    "category": "specific",
    "expected_chunks": ["fastapi-auth/jwt-tokens"],
    "min_score": 0.6,
    "description": "Specific JWT configuration query"
  },
  {
    "id": "q-async-await",
    "query": "Python async await syntax examples",
    "modes": ["semantic", "keyword", "hybrid"],
    "category": "specific",
    "expected_chunks": ["python-async/basics", "python-async/patterns"],
    "min_score": 0.7,
    "description": "Python async programming basics"
  }
]
```

#### 2. Broad Queries (Should find multiple results)

```json
[
  {
    "id": "q-api-security",
    "query": "API security authentication methods",
    "modes": ["semantic", "hybrid"],
    "category": "broad",
    "expected_chunks": [
      "fastapi-auth/intro",
      "fastapi-auth/oauth2-password",
      "graphql-api/auth"
    ],
    "min_score": 0.5,
    "description": "Broad security query across documents"
  },
  {
    "id": "q-programming-tutorial",
    "query": "programming tutorial for beginners",
    "modes": ["semantic", "hybrid"],
    "category": "broad",
    "expected_chunks": [
      "python-async/intro",
      "react-hooks/intro",
      "sql-basics/intro"
    ],
    "min_score": 0.4,
    "description": "Very broad query matching tutorials"
  }
]
```

#### 3. Negative Queries (Should NOT find relevant content)

```json
[
  {
    "id": "q-neg-unrelated",
    "query": "quantum computing algorithms",
    "modes": ["semantic", "keyword", "hybrid"],
    "category": "negative",
    "expected_chunks": [],
    "max_score": 0.4,
    "description": "Completely unrelated domain"
  },
  {
    "id": "q-neg-different-lang",
    "query": "Rust borrow checker ownership",
    "modes": ["semantic", "keyword", "hybrid"],
    "category": "negative",
    "expected_chunks": [],
    "max_score": 0.4,
    "description": "Different programming language"
  }
]
```

#### 4. Semantic-Only Queries (Synonym/Paraphrase)

```json
[
  {
    "id": "q-sem-synonym",
    "query": "secure web API authentication mechanisms",
    "modes": ["semantic"],
    "category": "specific",
    "expected_chunks": ["fastapi-auth/intro", "fastapi-auth/oauth2-password"],
    "min_score": 0.6,
    "description": "Synonyms should match semantically (OAuth2 ≈ authentication)"
  },
  {
    "id": "q-sem-paraphrase",
    "query": "making database queries efficiently",
    "modes": ["semantic"],
    "category": "specific",
    "expected_chunks": ["sql-basics/optimization"],
    "min_score": 0.5,
    "description": "Paraphrase of SQL query optimization"
  }
]
```

#### 5. Edge Case Queries

```json
[
  {
    "id": "q-edge-short",
    "query": "JWT",
    "modes": ["keyword", "hybrid"],
    "category": "edge",
    "expected_chunks": ["fastapi-auth/jwt-tokens"],
    "min_score": 0.5,
    "description": "Very short query (single term)"
  },
  {
    "id": "q-edge-long",
    "query": "I want to learn how to implement secure authentication in my FastAPI " +
      "application using OAuth2 password flow with JWT tokens and proper token " +
      "expiration handling for a production environment",
    "modes": ["semantic", "hybrid"],
    "category": "edge",
    "expected_chunks": ["fastapi-auth/oauth2-password", "fastapi-auth/jwt-tokens"],
    "min_score": 0.6,
    "description": "Very long query (near limit)"
  },
  {
    "id": "q-edge-special-chars",
    "query": "OAuth2.0 JWT (tokens) & API-keys",
    "modes": ["keyword", "hybrid"],
    "category": "edge",
    "expected_chunks": ["fastapi-auth/jwt-tokens"],
    "min_score": 0.4,
    "description": "Special characters in query"
  }
]
```

## Full Query Matrix

| ID | Query Summary | Semantic | Keyword | Hybrid | Category |
|----|---------------|----------|---------|--------|----------|
| q-oauth2-impl | OAuth2 FastAPI | ✅ | ✅ | ✅ | specific |
| q-jwt-expiry | JWT expiration | ✅ | ❌ | ✅ | specific |
| q-async-await | Python async | ✅ | ✅ | ✅ | specific |
| q-api-security | API security | ✅ | ❌ | ✅ | broad |
| q-programming | Programming tutorial | ✅ | ❌ | ✅ | broad |
| q-neg-unrelated | Quantum computing | ✅ | ✅ | ✅ | negative |
| q-neg-lang | Rust borrow checker | ✅ | ✅ | ✅ | negative |
| q-sem-synonym | Secure web API | ✅ | ❌ | ❌ | specific |
| q-sem-paraphrase | Database queries | ✅ | ❌ | ❌ | specific |
| q-edge-short | JWT | ❌ | ✅ | ✅ | edge |
| q-edge-long | Long OAuth2 query | ✅ | ❌ | ✅ | edge |
| q-edge-special | OAuth2.0 JWT& | ❌ | ✅ | ✅ | edge |

**Total: 12 queries × avg 2.5 modes = ~30 test cases**

## Coarse-to-Fine Queries

For two-stage retrieval testing:

```json
{
  "coarse_to_fine_queries": [
    {
      "id": "ctf-langchain-tools",
      "query": "LangChain tool calling patterns",
      "expected_coarse": ["langchain-agents/tools"],
      "expected_fine": ["langchain-agents/tools/para-1", "langchain-agents/tools/para-2"],
      "description": "Should find coarse section, then fine paragraphs"
    },
    {
      "id": "ctf-k8s-scaling",
      "query": "Kubernetes horizontal pod autoscaling",
      "expected_coarse": ["kubernetes-deploy/scaling"],
      "expected_fine": ["kubernetes-deploy/scaling/hpa-config"],
      "description": "DevOps coarse-to-fine"
    }
  ]
}
```

## Fixture Generation Script

```python
# scripts/generate_fixtures.py

"""Generate smoke test fixtures from templates."""

import json
from pathlib import Path


def generate_documents() -> dict:
    """Generate document fixtures."""
    return {
        "version": "1.0",
        "generated": "2025-12-10",
        "documents": [
            # Short documents
            create_fastapi_auth_doc(),
            create_python_async_doc(),
            create_react_hooks_doc(),
            create_sql_basics_doc(),
            # Long documents
            create_langchain_agents_doc(),
            create_kubernetes_deploy_doc(),
            create_graphql_api_doc(),
            create_ml_pipeline_doc(),
        ],
    }


def generate_queries() -> dict:
    """Generate query fixtures."""
    return {
        "version": "1.0",
        "generated": "2025-12-10",
        "queries": [
            # Specific queries
            *create_specific_queries(),
            # Broad queries
            *create_broad_queries(),
            # Negative queries
            *create_negative_queries(),
            # Semantic-only queries
            *create_semantic_queries(),
            # Edge case queries
            *create_edge_queries(),
        ],
        "coarse_to_fine": create_coarse_to_fine_queries(),
    }


def main():
    fixtures_dir = Path("tests/smoke/retrieval/fixtures")
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Generate and save documents
    docs = generate_documents()
    (fixtures_dir / "documents.json").write_text(
        json.dumps(docs, indent=2)
    )

    # Generate and save queries
    queries = generate_queries()
    (fixtures_dir / "queries.json").write_text(
        json.dumps(queries, indent=2)
    )

    print(f"Generated {len(docs['documents'])} documents")
    print(f"Generated {len(queries['queries'])} queries")


if __name__ == "__main__":
    main()
```

## Validation Rules

### Document Validation

```python
def validate_document(doc: dict) -> list[str]:
    """Validate a document fixture."""
    errors = []

    if not doc.get("id"):
        errors.append("Document missing 'id'")

    if doc.get("bucket") not in ("short", "long"):
        errors.append(f"Invalid bucket: {doc.get('bucket')}")

    sections = doc.get("sections", [])
    if not sections:
        errors.append("Document has no sections")

    for section in sections:
        if not section.get("id"):
            errors.append(f"Section missing 'id' in doc {doc['id']}")
        if not section.get("content"):
            errors.append(f"Section missing 'content' in doc {doc['id']}")

    return errors
```

### Query Validation

```python
def validate_query(query: dict, doc_ids: set[str]) -> list[str]:
    """Validate a query fixture against available documents."""
    errors = []

    if not query.get("id"):
        errors.append("Query missing 'id'")

    if not query.get("query"):
        errors.append(f"Query {query.get('id')} missing 'query' text")

    if not query.get("modes"):
        errors.append(f"Query {query.get('id')} missing 'modes'")

    # Validate expected chunks reference real documents
    for chunk_id in query.get("expected_chunks", []):
        doc_id = chunk_id.split("/")[0]
        if doc_id not in doc_ids:
            errors.append(
                f"Query {query['id']} references unknown doc: {doc_id}"
            )

    return errors
```

---

**Document Version:** 1.0
**Created:** December 10, 2025
