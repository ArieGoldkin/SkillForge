---
name: edge-caching
description: Edge caching with KV, Cache API, Durable Objects
version: 1.0.0
tags: [edge, caching, cloudflare, kv]
size: atomic
domain: devops
---

# Edge Caching

## Cache API

```typescript
async function handleRequest(request: Request) {
  const cache = caches.default
  const cacheKey = new Request(request.url, request)

  // Try cache first
  let response = await cache.match(cacheKey)

  if (!response) {
    response = await fetch(request)

    if (response.status === 200) {
      response = new Response(response.body, response)
      response.headers.set('Cache-Control', 'max-age=3600')
      await cache.put(cacheKey, response.clone())
    }
  }

  return response
}
```

## KV Storage

```typescript
export default {
  async fetch(request: Request, env: Env) {
    const ip = request.headers.get('CF-Connecting-IP')
    const key = `ratelimit:${ip}`

    // Get current count
    const count = await env.KV.get(key)
    const current = count ? parseInt(count) : 0

    if (current >= 100) {
      return new Response('Rate limit exceeded', { status: 429 })
    }

    await env.KV.put(key, (current + 1).toString(), {
      expirationTtl: 60  // 1 minute
    })

    return fetch(request)
  }
}
```

## Durable Objects (Stateful)

```typescript
export class Counter {
  private state: DurableObjectState
  private count = 0

  constructor(state: DurableObjectState) {
    this.state = state
  }

  async fetch(request: Request) {
    if (request.url.endsWith('/increment')) {
      this.count++
      await this.state.storage.put('count', this.count)
    }

    return new Response(JSON.stringify({ count: this.count }))
  }
}
```

## Caching Strategies

| Strategy | Use Case | TTL |
|----------|----------|-----|
| Static assets | Images, CSS, JS | 1 year |
| API responses | GET requests | 1-60 min |
| HTML pages | Marketing | 5 min |
| User data | Personalized | No cache |
