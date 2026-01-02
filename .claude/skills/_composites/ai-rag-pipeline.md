---
name: ai-rag-pipeline
description: Build RAG pipelines with embeddings, vector DBs, and retrieval patterns
version: 1.0.0
type: composite
includes:
  - ai-llm/embeddings
  - ai-llm/vector-databases
  - ai-llm/rag-patterns
trigger: "**/rag/**/*.py"
---

# AI RAG Pipeline

Complete guide for building Retrieval-Augmented Generation pipelines.

## When to Use

- Building knowledge base Q&A systems
- Creating document search applications
- Adding grounded AI responses to apps
- Implementing semantic search

## Pipeline Overview

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Documents   │ ──▶ │  Embeddings  │ ──▶ │  Vector DB   │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Response   │ ◀── │     LLM      │ ◀── │  Retrieval   │
└──────────────┘     └──────────────┘     └──────────────┘
```

## Included Skills

1. **embeddings** - Vector representations, chunking, similarity
2. **vector-databases** - Pinecone, Chroma, PGVector setup
3. **rag-patterns** - Basic RAG, HyDE, hybrid search, citations

## Quick Start

```python
# 1. Create embeddings
from langchain_ollama import OllamaEmbeddings
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# 2. Store in vector DB
from langchain_postgres import PGVector
vectorstore = PGVector(connection=conn, embeddings=embeddings)

# 3. Build RAG chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

llm = ChatOllama(model="qwen2.5-coder:32b")
retriever = vectorstore.as_retriever(k=5)

chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
)

answer = chain.invoke("How do I implement RAG?")
```

## See Also

- [embeddings](../_atomic/ai-llm/embeddings.md)
- [vector-databases](../_atomic/ai-llm/vector-databases.md)
- [rag-patterns](../_atomic/ai-llm/rag-patterns.md)
