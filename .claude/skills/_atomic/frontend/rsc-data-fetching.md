---
name: rsc-data-fetching
description: Next.js data fetching with caching and revalidation
version: 1.0.0
tags: [nextjs, data-fetching, caching, revalidation]
size: atomic
domain: frontend
---

# RSC Data Fetching

## Fetch with Caching

```tsx
// Static (cached indefinitely)
await fetch(url, { cache: 'force-cache' })

// Revalidate every 60 seconds
await fetch(url, { next: { revalidate: 60 } })

// Always fresh
await fetch(url, { cache: 'no-store' })

// Tag-based revalidation
await fetch(url, { next: { tags: ['posts'] } })
```

## Revalidation Methods

```tsx
import { revalidatePath, revalidateTag } from 'next/cache'

// Revalidate specific path
revalidatePath('/posts')

// Revalidate by tag
revalidateTag('posts')
```

## Parallel vs Sequential

```tsx
// ✅ Parallel (independent data)
const [users, posts] = await Promise.all([
  fetchUsers(),
  fetchPosts()
])

// Sequential (when data depends on previous)
const user = await fetchUser(id)
const posts = await fetchPosts(user.teamId)
```

## Static Generation

```tsx
export async function generateStaticParams() {
  const posts = await fetchPosts()
  return posts.map((post) => ({ slug: post.slug }))
}

export default async function PostPage({ params }) {
  const post = await fetchPost(params.slug)
  return <Post post={post} />
}
```

## Route Segment Config

```tsx
// Force dynamic
export const dynamic = 'force-dynamic'

// Force static
export const dynamic = 'force-static'

// Revalidate interval
export const revalidate = 60
```
