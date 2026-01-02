---
name: api-versioning-auth
description: API versioning strategies and authentication patterns
version: 1.0.0
tags: [api, versioning, authentication, jwt]
size: atomic
domain: backend
---

# API Versioning & Authentication

## Versioning Strategies

### URI Versioning (Recommended)

```
✅ /api/v1/users
✅ /api/v2/users

Pros: Clear, easy to test, cache-friendly
Cons: Verbose URLs
```

### Header Versioning

```
GET /api/users
Accept: application/vnd.company.v2+json

Pros: Clean URLs
Cons: Harder to test
```

### Query Parameter

```
GET /api/users?version=2

Pros: Simple
Cons: Can be forgotten
```

**Best Practice:** URI for public APIs, header for internal

## Authentication Patterns

### Bearer Token (JWT)

```
GET /users/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### API Key

```
GET /users
X-API-Key: sk_live_abc123...
```

### Basic Auth (avoid in production)

```
GET /users
Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=
```

## Idempotency Keys

Prevent duplicate operations:

```
POST /payments
Idempotency-Key: unique-request-id-123
```

## Webhook Signatures

```
POST https://client.example.com/webhook
X-Webhook-Signature: sha256=abc123...

{
  "event": "user.created",
  "data": { ... },
  "timestamp": "2025-10-31T10:30:00Z"
}
```

## CORS Headers

```
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Authorization, Content-Type
Access-Control-Max-Age: 86400
```

## Security Best Practices

- **Always HTTPS** in production
- **Short-lived tokens** (15-60 min)
- **Refresh tokens** for long sessions
- **Rate limiting** per API key/user
- **Audit logging** for sensitive operations
