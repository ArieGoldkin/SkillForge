---
name: api-frontend-integration
description: Frontend API integration with Zod validation
version: 1.0.0
tags: [api, frontend, zod, typescript, validation]
size: atomic
domain: backend
---

# Frontend API Integration

## Runtime Validation with Zod

TypeScript types are erased at runtime. Always validate API responses:

```typescript
import { z } from 'zod'

const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  name: z.string(),
  role: z.enum(['admin', 'developer', 'viewer']),
})

const UsersResponseSchema = z.object({
  data: z.array(UserSchema),
  pagination: z.object({
    next_cursor: z.string().nullable(),
    has_more: z.boolean(),
  }),
})

type User = z.infer<typeof UserSchema>

async function fetchUsers(): Promise<User[]> {
  const response = await fetch('/api/v1/users')
  const data = await response.json()
  return UsersResponseSchema.parse(data).data  // Runtime validation!
}
```

## Anti-Patterns

```typescript
// ❌ NEVER: Trust API blindly
const data = await response.json() as User  // Unsafe!

// ❌ NEVER: Skip validation
const user: User = await response.json()    // Crash waiting to happen

// ✅ ALWAYS: Validate at boundary
const user = UserSchema.parse(await response.json())
```

## Request Client with ky

```typescript
import ky from 'ky'

export const api = ky.create({
  prefixUrl: import.meta.env.VITE_API_URL,
  timeout: 30000,
  retry: {
    limit: 2,
    statusCodes: [408, 429, 500, 502, 503, 504],
  },
  hooks: {
    beforeRequest: [
      async (request) => {
        const token = await getAccessToken()
        if (token) {
          request.headers.set('Authorization', `Bearer ${token}`)
        }
      },
    ],
    afterResponse: [
      async (request, options, response) => {
        if (response.status === 401) {
          const newToken = await refreshToken()
          if (newToken) {
            request.headers.set('Authorization', `Bearer ${newToken}`)
            return ky(request, options)
          }
        }
        return response
      },
    ],
  },
})
```

## Structured API Errors

```typescript
class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: Array<{ field: string; message: string }>
  ) {
    super(message)
  }

  get isValidationError() { return this.status === 422 }
  get isAuthError() { return this.status === 401 || this.status === 403 }
  get isRateLimited() { return this.status === 429 }
}
```

## TanStack Query Integration

```typescript
import { useQuery } from '@tanstack/react-query'

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const data = await api.get('users').json()
      return UsersResponseSchema.parse(data)
    },
    staleTime: 30_000,
  })
}
```
