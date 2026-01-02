---
name: rag-retrieval
description: Retrieval-Augmented Generation patterns for grounded LLM responses. Use when building RAG pipelines, constructing context from retrieved documents, adding citations, or implementing hybrid search.
---

# RAG Retrieval

Combine vector search with LLM generation for accurate, grounded responses.

## When to Use

- Q&A systems over documents
- Chatbots with knowledge bases
- Search with natural language answers
- Grounding LLM responses in facts

## Basic RAG Pattern

```python
async def rag_query(question: str, top_k: int = 5) -> str:
    """Basic RAG: retrieve then generate."""
    # 1. Retrieve relevant documents
    docs = await vector_db.search(question, limit=top_k)

    # 2. Construct context
    context = "\n\n".join([
        f"[{i+1}] {doc.text}"
        for i, doc in enumerate(docs)
    ])

    # 3. Generate with context
    response = await llm.chat([
        {"role": "system", "content":
            "Answer using ONLY the provided context. "
            "If not in context, say 'I don't have that information.'"},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
    ])

    return response.content
```

## RAG with Citations

```python
async def rag_with_citations(question: str) -> dict:
    """RAG with inline citations [1], [2], etc."""
    docs = await vector_db.search(question, limit=5)

    context = "\n\n".join([
        f"[{i+1}] {doc.text}\nSource: {doc.metadata['source']}"
        for i, doc in enumerate(docs)
    ])

    response = await llm.chat([
        {"role": "system", "content":
            "Answer with inline citations like [1], [2]. "
            "End with a Sources section."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
    ])

    return {
        "answer": response.content,
        "sources": [doc.metadata['source'] for doc in docs]
    }
```

## Hybrid Search (Semantic + Keyword)

```python
def reciprocal_rank_fusion(
    semantic_results: list,
    keyword_results: list,
    k: int = 60
) -> list:
    """Combine semantic and keyword search with RRF."""
    scores = {}

    for rank, doc in enumerate(semantic_results):
        scores[doc.id] = scores.get(doc.id, 0) + 1 / (k + rank + 1)

    for rank, doc in enumerate(keyword_results):
        scores[doc.id] = scores.get(doc.id, 0) + 1 / (k + rank + 1)

    # Sort by combined score
    ranked_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [get_doc(id) for id in ranked_ids]
```

## Context Window Management

```python
def fit_context(docs: list, max_tokens: int = 6000) -> list:
    """Truncate context to fit token budget."""
    total_tokens = 0
    selected = []

    for doc in docs:
        doc_tokens = count_tokens(doc.text)
        if total_tokens + doc_tokens > max_tokens:
            break
        selected.append(doc)
        total_tokens += doc_tokens

    return selected
```

**Guidelines:**
- Keep context under 75% of model limit
- Reserve tokens for system prompt + response
- Prioritize highest-relevance documents

## Key Decisions

| Decision | Recommendation |
|----------|----------------|
| Top-k | 3-10 documents |
| Temperature | 0.1-0.3 (factual) |
| Context budget | 4K-8K tokens |
| Hybrid ratio | 50/50 semantic/keyword |

## Common Mistakes

- No citation tracking (unverifiable answers)
- Context too large (dilutes relevance)
- Temperature too high (hallucinations)
- Single retrieval method (misses keyword matches)

## Related Skills

- `embeddings` - Creating vectors for retrieval
- `pgvector-search` - Hybrid search with PostgreSQL
- `hyde-search` - Hypothetical document embeddings
