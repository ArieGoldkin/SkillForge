---
name: edge-computing
description: Edge computing with Cloudflare Workers and Vercel Edge
version: 1.0.0
tags: [edge, cloudflare, vercel, serverless]
size: composite
atomics:
  - devops/edge-workers
  - devops/edge-caching
---

# Edge Computing Composite

Deploy globally distributed, low-latency applications.

## When to Use

- Global apps requiring <50ms latency
- Auth/rate limiting at edge
- A/B testing and feature flags
- Geo-routing and localization

## Atomic Skills

### 1. Edge Workers (`edge-workers`)
Cloudflare Workers, Vercel Edge Functions, runtime constraints.

### 2. Edge Caching (`edge-caching`)
KV storage, Cache API, Durable Objects.

## Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│  EDGE DECISION TREE                                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Auth/rate limiting? ──► Edge Worker + KV                   │
│  A/B testing? ──► Edge Middleware                           │
│  Geo-routing? ──► Edge Worker + request.cf.country          │
│  Stateful counter? ──► Durable Objects                      │
│  Cache API responses? ──► Edge Cache API                    │
│                                                             │
│  Platform choice:                                           │
│  - 300+ locations? ──► Cloudflare Workers                   │
│  - Next.js native? ──► Vercel Edge                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Load Order

1. `edge-workers` - Understand edge runtime
2. `edge-caching` - Add caching layer
