---
name: api-pagination
description: Pagination, filtering, and sorting strategies
version: 1.0.0
tags: [api, pagination, filtering, sorting]
size: atomic
domain: backend
---

# API Pagination & Filtering

## Cursor-Based Pagination (Recommended)

```
GET /users?cursor=eyJpZCI6MTIzfQ&limit=20

Response:
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTQzfQ",
    "has_more": true
  }
}
```

**Pros:** Consistent results, handles real-time data
**Use for:** Large datasets, infinite scroll

## Offset-Based Pagination

```
GET /users?page=2&per_page=20

Response:
{
  "data": [...],
  "pagination": {
    "page": 2,
    "per_page": 20,
    "total": 487,
    "total_pages": 25
  }
}
```

**Pros:** Easy to understand, supports "jump to page"
**Use for:** Small datasets, admin panels

## Filtering

```
GET /users?status=active&role=developer&created_after=2025-01-01
GET /products?price_min=10&price_max=100&category=electronics
```

## Sorting

```
GET /users?sort=created_at:desc
GET /users?sort=-created_at                 # Minus = descending
GET /users?sort=name:asc,created_at:desc   # Multiple fields
```

## Field Selection

```
GET /users?fields=id,name,email           # Only specified
GET /users/123?exclude=password_hash      # All except
```

## Rate Limiting Headers

```
HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1635724800

HTTP/1.1 429 Too Many Requests
Retry-After: 3600
```

## Best Practices

- **Default limit:** 20-50 items
- **Max limit:** 100-200 items
- **Cursor:** Base64 encode position
- **Total count:** Optional (expensive for large datasets)
