---
name: trpc-api
description: tRPC type-safe API procedures
version: 1.0.0
tags: [typescript, trpc, api, type-safety]
size: atomic
domain: frontend
---

# tRPC Type-Safe APIs

## Server Setup

```typescript
import { initTRPC } from '@trpc/server'
import { z } from 'zod'

const t = initTRPC.create()

export const appRouter = t.router({
  getUser: t.procedure
    .input(z.object({ id: z.string() }))
    .query(async ({ input }) => {
      return await db.user.findUnique({ where: { id: input.id } })
    }),

  createUser: t.procedure
    .input(z.object({
      email: z.string().email(),
      name: z.string()
    }))
    .mutation(async ({ input }) => {
      return await db.user.create({ data: input })
    })
})

export type AppRouter = typeof appRouter
```

## Client Setup

```typescript
import { createTRPCProxyClient, httpBatchLink } from '@trpc/client'
import type { AppRouter } from './server'

const client = createTRPCProxyClient<AppRouter>({
  links: [httpBatchLink({ url: 'http://localhost:3000/api/trpc' })]
})

// Fully typed!
const user = await client.getUser.query({ id: '123' })
```

## React Query Integration

```typescript
import { createTRPCReact } from '@trpc/react-query'
import type { AppRouter } from '@/server/routers/_app'

export const trpc = createTRPCReact<AppRouter>()

// In component
function UserList() {
  const { data, isLoading } = trpc.users.list.useQuery({ limit: 10 })
  const createUser = trpc.users.create.useMutation()

  return (
    <div>
      {data?.map(user => <User key={user.id} user={user} />)}
      <button onClick={() => createUser.mutate({ name: 'New' })}>
        Add User
      </button>
    </div>
  )
}
```

## Next.js Route Handler

```typescript
// app/api/trpc/[trpc]/route.ts
import { fetchRequestHandler } from '@trpc/server/adapters/fetch'
import { appRouter } from '@/server/routers/_app'

export async function GET(req: Request) {
  return fetchRequestHandler({
    endpoint: '/api/trpc',
    req,
    router: appRouter,
    createContext: () => ({})
  })
}

export const POST = GET
```

## Best Practices

- ✅ Use batching for multiple queries
- ✅ Define input schemas with Zod
- ✅ Export AppRouter type for client
- ✅ Use React Query hooks in components
