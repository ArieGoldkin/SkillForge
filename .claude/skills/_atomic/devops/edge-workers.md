---
name: edge-workers
description: Cloudflare Workers and Vercel Edge Functions
version: 1.0.0
tags: [edge, cloudflare, vercel, serverless]
size: atomic
domain: devops
---

# Edge Workers

## Platform Comparison

| Feature | Cloudflare | Vercel Edge |
|---------|------------|-------------|
| Cold Start | <1ms | <10ms |
| Locations | 300+ | 100+ |
| Free Tier | 100k/day | 100k/month |

## Cloudflare Worker

```typescript
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url)
    const country = request.cf?.country || 'US'

    if (url.pathname === '/api/hello') {
      return new Response(JSON.stringify({
        message: `Hello from ${country}!`
      }), {
        headers: { 'Content-Type': 'application/json' }
      })
    }

    return fetch(request)
  }
}
```

## Vercel Edge Middleware

```typescript
// middleware.ts
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  // A/B testing
  const bucket = Math.random() < 0.5 ? 'a' : 'b'
  const url = request.nextUrl.clone()
  url.searchParams.set('bucket', bucket)

  const response = NextResponse.rewrite(url)
  response.cookies.set('bucket', bucket)
  return response
}

export const config = {
  matcher: '/experiment/:path*'
}
```

## Edge Runtime Constraints

**Available**:
- fetch, Request, Response
- TextEncoder, TextDecoder
- crypto, SubtleCrypto
- ReadableStream, WritableStream

**NOT Available**:
- Node.js APIs (fs, path, etc.)
- Native modules
- File system access

## Best Practices

- ✅ Keep bundles small (<1MB)
- ✅ Use streaming for large responses
- ✅ Handle errors gracefully
- ✅ Test cold starts
