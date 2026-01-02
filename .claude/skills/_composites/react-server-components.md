---
name: react-server-components
description: Complete React Server Components with Next.js 15 App Router
version: 1.0.0
tags: [react, nextjs, server-components, streaming]
size: composite
atomics:
  - frontend/rsc-fundamentals
  - frontend/rsc-data-fetching
  - frontend/rsc-server-actions
  - frontend/rsc-streaming
  - frontend/react-19-patterns
---

# React Server Components Composite

Complete RSC knowledge for Next.js 15 App Router development.

## When to Use

- Building Next.js 15+ applications
- Designing Server vs Client component boundaries
- Implementing data fetching with caching
- Creating mutations with Server Actions
- Optimizing with streaming and Suspense

## Atomic Skills

### 1. RSC Fundamentals (`rsc-fundamentals`)
Server vs Client components, boundary rules, composition patterns.

### 2. Data Fetching (`rsc-data-fetching`)
Fetch with caching, revalidation, tags, parallel/sequential patterns.

### 3. Server Actions (`rsc-server-actions`)
Mutations without API routes, Zod validation, useActionState.

### 4. Streaming (`rsc-streaming`)
Suspense, loading.tsx, PPR, error boundaries.

### 5. React 19 Patterns (`react-19-patterns`)
Function declarations, ref as prop, useOptimistic.

## Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│  RSC DECISION TREE                                          │
├─────────────────────────────────────────────────────────────┤
│  Need hooks/browser APIs? ──► Client Component              │
│  Need async/DB access? ──► Server Component                 │
│  Need both? ──► Server parent + Client child                │
│                                                             │
│  Static data? ──► cache: 'force-cache'                      │
│  Real-time? ──► cache: 'no-store'                           │
│  Timed refresh? ──► next: { revalidate: 60 }                │
└─────────────────────────────────────────────────────────────┘
```

## Load Order

1. `rsc-fundamentals` - Understand boundaries
2. `rsc-data-fetching` - Implement data loading
3. `rsc-server-actions` - Handle mutations
4. `rsc-streaming` - Optimize UX
5. `react-19-patterns` - Use latest patterns
