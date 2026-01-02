---
name: rag-patterns
description: Retrieval-Augmented Generation patterns for grounded AI responses
version: 1.0.0
tags: [ai, llm, rag, retrieval, generation, hyde, hybrid-search]
size: atomic
domain: ai-llm
---

# RAG Patterns

## Basic RAG

```typescript
async function ragQuery(question: string): Promise<string> {
  // 1. Retrieve relevant documents
  const relevantDocs = await queryDocuments(question, 5)

  // 2. Construct context
  const context = relevantDocs
    .map((doc, i) => `[${i + 1}] ${doc.text}`)
    .join('\n\n')

  // 3. Generate answer with context
  const response = await openai.chat.completions.create({
    model: 'gpt-4-turbo-preview',
    messages: [
      {
        role: 'system',
        content: `Answer ONLY using the provided context. If not in context, say "I don't have enough information."`
      },
      { role: 'user', content: `Context:\n${context}\n\nQuestion: ${question}` }
    ],
    temperature: 0.1
  })

  return response.choices[0].message.content!
}
```

## RAG with Citations

```typescript
async function ragWithCitations(question: string) {
  const docs = await queryDocuments(question, 5)
  const context = docs.map((d, i) => `[${i + 1}] ${d.text}\nSource: ${d.source}`).join('\n\n')

  const response = await openai.chat.completions.create({
    model: 'gpt-4-turbo-preview',
    messages: [{
      role: 'system',
      content: 'Answer with inline citations [1], [2], etc. End with Sources section.'
    }, {
      role: 'user',
      content: `Context:\n${context}\n\nQuestion: ${question}`
    }]
  })

  return { answer: response.choices[0].message.content!, sources: docs }
}
```

## Hybrid Search (Semantic + Keyword)

```typescript
function reciprocalRankFusion(
  semanticResults: Doc[],
  keywordResults: Doc[],
  k = 60
): Doc[] {
  const scores = new Map<string, number>()

  semanticResults.forEach((doc, rank) => {
    scores.set(doc.id, (scores.get(doc.id) || 0) + 1 / (k + rank + 1))
  })

  keywordResults.forEach((doc, rank) => {
    scores.set(doc.id, (scores.get(doc.id) || 0) + 1 / (k + rank + 1))
  })

  return Array.from(scores.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([id]) => semanticResults.find(r => r.id === id) || keywordResults.find(r => r.id === id)!)
}
```

## HyDE (Hypothetical Document Embeddings)

Generate a hypothetical answer, then use it for retrieval:

```typescript
async function hydeRAG(question: string) {
  // 1. Generate hypothetical answer
  const hypothetical = await openai.chat.completions.create({
    model: 'gpt-3.5-turbo',
    messages: [{
      role: 'system',
      content: 'Write a detailed answer as if you had the information.'
    }, { role: 'user', content: question }]
  })

  // 2. Use hypothetical for retrieval (better embedding match)
  const docs = await queryDocuments(hypothetical.choices[0].message.content!, 5)

  // 3. Generate real answer from retrieved docs
  return ragQuery(question, docs)
}
```

## Best Practices

- **Context window**: Keep under 75% of model limit
- **Temperature**: Low (0.1-0.3) for factual answers
- **Hybrid search**: 3x fetch multiplier for RRF fusion
- **Validation**: Check if answer is grounded in sources
