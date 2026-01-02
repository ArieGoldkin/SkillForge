---
name: api-design
description: Comprehensive API design patterns for REST and GraphQL
version: 1.0.0
tags: [api, rest, graphql, backend, design]
size: composite
atomics:
  - backend/api-rest-patterns
  - backend/api-pagination
  - backend/api-graphql
  - backend/api-versioning-auth
  - backend/api-frontend-integration
---

# API Design Composite

Complete API design knowledge combining REST patterns, pagination, GraphQL, versioning, and frontend integration.

## When to Use

- Designing new REST or GraphQL APIs
- Adding pagination/filtering to endpoints
- Implementing authentication and versioning
- Building type-safe frontend API clients

## Atomic Skills

### 1. REST Patterns (`api-rest-patterns`)
Resource naming, HTTP methods, status codes, error responses.

### 2. Pagination (`api-pagination`)
Cursor vs offset pagination, filtering, sorting strategies.

### 3. GraphQL (`api-graphql`)
Schema design, connections, mutations, N+1 prevention.

### 4. Versioning & Auth (`api-versioning-auth`)
URL/header versioning, JWT/OAuth patterns.

### 5. Frontend Integration (`api-frontend-integration`)
Zod validation, ky client, type-safe API consumption.

## Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│  API DESIGN DECISION TREE                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Need flexible queries? ──► GraphQL                         │
│  Simple CRUD? ──► REST                                      │
│                                                             │
│  Large datasets? ──► Cursor pagination                      │
│  Small datasets? ──► Offset pagination                      │
│                                                             │
│  Breaking changes? ──► URL versioning (/v2/)                │
│  Additive changes? ──► No version needed                    │
│                                                             │
│  Frontend type safety? ──► Zod + ky client                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Load Order

1. Start with `api-rest-patterns` for fundamentals
2. Add `api-pagination` for list endpoints
3. Consider `api-graphql` for complex queries
4. Apply `api-versioning-auth` for production
5. Use `api-frontend-integration` for client code
