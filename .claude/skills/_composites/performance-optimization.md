---
name: performance-optimization
description: Full-stack performance optimization - frontend, backend, database
version: 1.0.0
tags: [performance, optimization, web-vitals, database]
size: composite
atomics:
  - tools/performance-targets
  - tools/db-query-optimization
  - tools/frontend-bundle
---

# Performance Optimization

## Load Order

```yaml
1. tools/performance-targets      # Targets and metrics definitions
2. tools/db-query-optimization    # N+1, EXPLAIN, indexes
3. tools/frontend-bundle          # Bundle analysis, code splitting
```

## Optimization Flow

```
┌─────────────────────────────────────────────────────────────┐
│              PERFORMANCE OPTIMIZATION FLOW                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. MEASURE                                                 │
│     ├── Core Web Vitals (LCP, INP, CLS)                    │
│     ├── Backend latency (p50, p95, p99)                    │
│     └── Database query times                                │
│                                                             │
│  2. IDENTIFY BOTTLENECKS                                    │
│     ├── Network: High TTFB → CDN, caching                  │
│     ├── Database: Slow queries → EXPLAIN, indexes          │
│     ├── Frontend: Large bundles → Code splitting           │
│     └── CPU: High utilization → Profiling                  │
│                                                             │
│  3. OPTIMIZE                                                │
│     ├── Database: Add indexes, eager loading               │
│     ├── Frontend: Tree-shaking, lazy routes                │
│     └── Backend: Caching, query optimization               │
│                                                             │
│  4. VERIFY                                                  │
│     └── Re-measure against targets                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Quick Reference

### Frontend Targets
- LCP < 2.5s | INP < 200ms | CLS < 0.1
- Bundle (gzip) < 200KB | Main entry < 50KB

### Backend Targets
- Simple reads < 100ms | Complex queries < 500ms
- LLM calls < 3s | Index lookups < 10ms

### Common Fixes

| Problem | Solution |
|---------|----------|
| N+1 queries | `selectinload()` eager loading |
| Slow searches | Add GIN/HNSW index |
| Large bundles | Dynamic imports, tree-shaking |
| High TTFB | Edge caching, CDN |
