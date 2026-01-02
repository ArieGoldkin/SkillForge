---
name: performance-targets
description: Performance targets for Core Web Vitals and backend
version: 1.0.0
tags: [performance, web-vitals, latency, targets]
size: atomic
domain: tools
---

# Performance Targets

## Core Web Vitals (Frontend)

| Metric | Good | Needs Work | Poor |
|--------|------|------------|------|
| **LCP** | < 2.5s | 2.5-4s | > 4s |
| **INP** | < 200ms | 200-500ms | > 500ms |
| **CLS** | < 0.1 | 0.1-0.25 | > 0.25 |
| **TTFB** | < 200ms | 200-600ms | > 600ms |

**LCP** = Largest Contentful Paint
**INP** = Interaction to Next Paint
**CLS** = Cumulative Layout Shift
**TTFB** = Time to First Byte

## Backend Targets

| Operation | Target | Acceptable |
|-----------|--------|------------|
| Simple reads | < 100ms | < 200ms |
| Complex queries | < 500ms | < 1s |
| Write operations | < 200ms | < 500ms |
| Index lookups | < 10ms | < 50ms |
| LLM calls | < 3s | < 5s |

## Bottleneck Categories

| Category | Symptoms | Tools |
|----------|----------|-------|
| **Network** | High TTFB | Network tab |
| **Database** | Slow queries | EXPLAIN ANALYZE |
| **CPU** | High usage | Profiler |
| **Memory** | Leaks, GC | Heap snapshots |
| **Rendering** | Layout thrash | Performance tab |

## Analysis Commands

```bash
# Lighthouse audit
lighthouse http://localhost:3000 --output=json

# Bundle analysis
npx vite-bundle-visualizer
npx @next/bundle-analyzer

# Database slow queries (PostgreSQL)
SELECT query, mean_time / 1000 as mean_sec
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
```

## Monitoring Checklist

### Before Launch
- [ ] Lighthouse score > 90
- [ ] Core Web Vitals pass
- [ ] Bundle size within budget
- [ ] Database queries profiled
- [ ] Compression enabled

### Ongoing
- [ ] Performance monitoring active
- [ ] Alerting for degradation
- [ ] Lighthouse CI in pipeline
- [ ] Weekly query analysis
