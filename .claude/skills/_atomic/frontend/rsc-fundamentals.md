---
name: rsc-fundamentals
description: React Server Components vs Client Components and boundary rules
version: 1.0.0
tags: [react, server-components, nextjs, boundaries]
size: atomic
domain: frontend
---

# RSC Fundamentals

## Server vs Client Components

**Server Components** (default):
```tsx
export default async function UsersPage() {
  const users = await db.user.findMany()
  return <UserList users={users} />
}
```

**Client Components** (`'use client'`):
```tsx
'use client'
import { useState } from 'react'

export function Counter() {
  const [count, setCount] = useState(0)
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>
}
```

## Comparison

| Feature | Server | Client |
|---------|--------|--------|
| async/await | ✅ | ❌ |
| Hooks | ❌ | ✅ |
| Browser APIs | ❌ | ✅ |
| DB access | ✅ | ❌ |
| JS bundle | None | Shipped |

## Composition Pattern

Pass Server Components as `children`:

```tsx
// ClientWrapper.tsx
'use client'
export function ClientWrapper({ children }) {
  const [open, setOpen] = useState(false)
  return <div onClick={() => setOpen(!open)}>{children}</div>
}

// page.tsx (Server)
export default async function Page() {
  const data = await fetchData()
  return (
    <ClientWrapper>
      <ServerDataDisplay data={data} />
    </ClientWrapper>
  )
}
```

## Best Practices

- ✅ Keep Client Components at tree edges
- ✅ Server Components by default
- ❌ Don't make entire pages Client Components
