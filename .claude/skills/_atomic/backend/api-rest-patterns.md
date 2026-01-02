---
name: api-rest-patterns
description: REST API naming conventions, HTTP methods, status codes
version: 1.0.0
tags: [api, rest, http, conventions]
size: atomic
domain: backend
---

# REST API Patterns

## Resource Naming

```
✅ GET /users              # Plural nouns
✅ GET /users/123          # Specific resource
✅ GET /users/123/orders   # Hierarchical

❌ GET /user               # Singular
❌ GET /getUser            # Verb in URL
❌ GET /userOrders/123     # Flat structure
```

**Use kebab-case for multi-word:**
```
✅ /shopping-carts
✅ /order-items

❌ /shoppingCarts    (camelCase)
❌ /shopping_carts   (snake_case)
```

## HTTP Methods

| Method | Purpose | Idempotent | Safe |
|--------|---------|------------|------|
| **GET** | Retrieve | Yes | Yes |
| **POST** | Create | No | No |
| **PUT** | Replace entire | Yes | No |
| **PATCH** | Partial update | No* | No |
| **DELETE** | Remove | Yes | No |

## Status Codes

### Success (2xx)
- **200 OK**: GET, PUT, PATCH, DELETE success
- **201 Created**: POST success (include `Location` header)
- **204 No Content**: DELETE with no body

### Client Errors (4xx)
- **400 Bad Request**: Invalid request
- **401 Unauthorized**: Missing/invalid auth
- **403 Forbidden**: Authenticated but not authorized
- **404 Not Found**: Resource doesn't exist
- **409 Conflict**: Resource conflict (duplicate)
- **422 Unprocessable Entity**: Validation failed
- **429 Too Many Requests**: Rate limit

### Server Errors (5xx)
- **500 Internal Server Error**: Generic
- **502 Bad Gateway**: Upstream error
- **503 Service Unavailable**: Temporary

## Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "message": "Email already registered",
        "code": "DUPLICATE_EMAIL"
      }
    ],
    "request_id": "req_abc123"
  }
}
```

## Common Pitfalls

```
❌ POST /createUser       → ✅ POST /users
❌ POST /users/123/delete → ✅ DELETE /users/123
❌ /users-table           → ✅ /users
```
