---
name: embeddings
description: Vector representations of text for semantic search
version: 1.0.0
tags: [ai, llm, embeddings, vectors, similarity]
size: atomic
domain: ai-llm
---

# Embeddings

## Core Concept

Embeddings convert text into high-dimensional vectors (1536-3072 dimensions) that capture semantic meaning. Similar concepts have similar vectors.

## Creating Embeddings

```typescript
import OpenAI from 'openai'

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY })

async function createEmbedding(text: string): Promise<number[]> {
  const response = await openai.embeddings.create({
    model: 'text-embedding-3-small', // 1536 dims, cheaper
    // model: 'text-embedding-3-large', // 3072 dims, better quality
    input: text,
  })
  return response.data[0].embedding
}

// Batch processing (up to 2048 texts)
async function createEmbeddings(texts: string[]): Promise<number[][]> {
  const response = await openai.embeddings.create({
    model: 'text-embedding-3-small',
    input: texts,
  })
  return response.data.map(d => d.embedding)
}
```

## Similarity Search

```typescript
function cosineSimilarity(a: number[], b: number[]): number {
  const dotProduct = a.reduce((sum, val, i) => sum + val * b[i], 0)
  const magnitudeA = Math.sqrt(a.reduce((sum, val) => sum + val * val, 0))
  const magnitudeB = Math.sqrt(b.reduce((sum, val) => sum + val * val, 0))
  return dotProduct / (magnitudeA * magnitudeB)
}

async function findSimilar(query: string, documents: Document[], topK = 5) {
  const queryEmbedding = await createEmbedding(query)

  return documents
    .map(doc => ({ doc, score: cosineSimilarity(queryEmbedding, doc.embedding) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, topK)
}
```

## Chunking Strategy

```typescript
function chunkDocument(text: string, chunkSize = 1000, overlap = 200): string[] {
  const chunks: string[] = []
  let start = 0

  while (start < text.length) {
    const end = Math.min(start + chunkSize, text.length)
    chunks.push(text.slice(start, end))
    start = end - overlap
  }

  return chunks
}
```

## Best Practices

- **Chunk size**: 500-1000 tokens with 10-20% overlap
- **Batch processing**: Use batch API for efficiency (up to 2048 texts)
- **Caching**: Cache embeddings to avoid recomputation
- **Re-embed**: When source content changes, regenerate embeddings
