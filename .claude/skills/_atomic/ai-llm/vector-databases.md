---
name: vector-databases
description: Store and retrieve embeddings efficiently at scale
version: 1.0.0
tags: [ai, llm, vector-database, pinecone, chroma, qdrant, pgvector]
size: atomic
domain: ai-llm
---

# Vector Databases

## Overview

Vector databases store embeddings and enable fast similarity search. Choose based on your needs:

| Provider | Type | Best For | Cost |
|----------|------|----------|------|
| **Pinecone** | Serverless | Production, managed | $0.096/hour |
| **Chroma** | Self-hosted | Development, on-prem | Free (OSS) |
| **Qdrant** | Self-hosted | High performance | Free (OSS) |
| **PGVector** | PostgreSQL extension | Existing Postgres | Free |

## Pinecone (Serverless)

```typescript
import { Pinecone } from '@pinecone-database/pinecone'

const pinecone = new Pinecone({ apiKey: process.env.PINECONE_API_KEY! })
const index = pinecone.index('documents')

// Upsert
await index.upsert(documents.map((doc, i) => ({
  id: doc.id,
  values: embeddings[i],
  metadata: { text: doc.text, ...doc.metadata }
})))

// Query
const results = await index.query({
  vector: queryEmbedding,
  topK: 5,
  includeMetadata: true,
  filter: { category: { $eq: 'docs' } }
})
```

## Chroma (Open Source)

```typescript
import { ChromaClient } from 'chromadb'

const client = new ChromaClient({ path: 'http://localhost:8000' })
const collection = await client.createCollection({ name: 'documents' })

// Add
await collection.add({
  ids: documents.map(d => d.id),
  embeddings: embeddings,
  metadatas: documents.map(d => d.metadata),
})

// Query
const results = await collection.query({
  queryEmbeddings: [queryEmbedding],
  nResults: 5,
  where: { category: 'docs' }
})
```

## PGVector (PostgreSQL)

```sql
-- Enable extension
CREATE EXTENSION vector;

-- Create table with vector column
CREATE TABLE chunks (
  id UUID PRIMARY KEY,
  content TEXT,
  embedding vector(1536)
);

-- Create HNSW index (17x faster than IVFFlat)
CREATE INDEX idx_chunks_embedding ON chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Query
SELECT id, content, 1 - (embedding <=> $1) AS similarity
FROM chunks
ORDER BY embedding <=> $1
LIMIT 10;
```

## Best Practices

- **Use HNSW indexes**: 17x faster than IVFFlat (5ms vs 85ms)
- **Metadata filtering**: Narrow search space before vector similarity
- **Hybrid search**: Combine semantic + keyword for better recall
- **Batch upserts**: Process 100-1000 vectors per batch
