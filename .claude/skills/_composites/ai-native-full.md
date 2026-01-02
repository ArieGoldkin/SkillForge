---
name: ai-native-full
description: Complete AI-native development stack - RAG, agents, streaming, caching
version: 1.0.0
type: composite
includes:
  - ai-rag-pipeline
  - ai-agent-workflow
  - ai-llm/streaming-responses
  - ai-llm/cost-optimization
  - llm-caching
trigger: "**/ai/**/*.py"
---

# AI-Native Full Stack

Complete guide for building AI-first applications with production-ready patterns.

## When to Use

- Building full AI-powered applications
- Implementing end-to-end AI pipelines
- Optimizing AI systems for production
- Reducing LLM API costs at scale

## Full Stack Overview

```
┌────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                │
│              (SSE streaming, real-time updates)                │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────┐
│                      API LAYER                                 │
│         (FastAPI + streaming endpoints)                        │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────┐
│                    CACHING LAYER                               │
│    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│    │Prompt Cache │ │Semantic     │ │ Query Cache │            │
│    │(Claude)     │ │Cache (Redis)│ │ (PG)        │            │
│    └─────────────┘ └─────────────┘ └─────────────┘            │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────┐
│                    AI WORKFLOW                                 │
│    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│    │ RAG         │ │ Multi-Agent │ │ Tool Use    │            │
│    │ Pipeline    │ │ Orchestrator│ │ Functions   │            │
│    └─────────────┘ └─────────────┘ └─────────────┘            │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────┐
│                    DATA LAYER                                  │
│    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│    │ PostgreSQL  │ │ PGVector    │ │ Redis       │            │
│    │ (structured)│ │ (embeddings)│ │ (cache)     │            │
│    └─────────────┘ └─────────────┘ └─────────────┘            │
└────────────────────────────────────────────────────────────────┘
```

## Cost Optimization Results

```
Baseline (no optimization):    $35,000/year
With prompt caching (90%):     -$31,500
With semantic cache (75%):     -$2,625
Final cost:                    $875/year (97.5% reduction)
```

## Included Components

### Composites
- **ai-rag-pipeline** - Embeddings, vector DBs, RAG patterns
- **ai-agent-workflow** - Agents, orchestration, synthesis
- **llm-caching** - Multi-level caching hierarchy

### Atomics
- **streaming-responses** - SSE, backpressure, real-time
- **cost-optimization** - Model selection, batching, caching

## See Also

- [ai-rag-pipeline](./ai-rag-pipeline.md)
- [ai-agent-workflow](./ai-agent-workflow.md)
- [llm-caching](./llm-caching.md)
