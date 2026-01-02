---
name: rsc-server-actions
description: Server Actions for mutations without API routes
version: 1.0.0
tags: [nextjs, server-actions, forms, mutations]
size: atomic
domain: frontend
---

# Server Actions

## Basic Pattern

```tsx
// app/actions.ts
'use server'

import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'

export async function createPost(formData: FormData) {
  const title = formData.get('title') as string
  const post = await db.post.create({ data: { title } })

  revalidatePath('/posts')
  redirect(`/posts/${post.id}`)
}
```

## Form Usage

```tsx
// page.tsx
import { createPost } from './actions'

export default function NewPost() {
  return (
    <form action={createPost}>
      <input name="title" required />
      <button type="submit">Create</button>
    </form>
  )
}
```

## With Validation (Zod)

```tsx
'use server'

import { z } from 'zod'

const schema = z.object({
  title: z.string().min(1).max(200),
  content: z.string().optional()
})

export async function createPost(formData: FormData) {
  const result = schema.safeParse({
    title: formData.get('title'),
    content: formData.get('content')
  })

  if (!result.success) {
    return { error: result.error.flatten() }
  }

  await db.post.create({ data: result.data })
  revalidatePath('/posts')
}
```

## useActionState (React 19)

```tsx
'use client'

import { useActionState } from 'react'

export function Form() {
  const [state, formAction, isPending] = useActionState(createPost, {
    message: '',
    success: false
  })

  return (
    <form action={formAction}>
      <input name="title" disabled={isPending} />
      <button disabled={isPending}>
        {isPending ? 'Saving...' : 'Save'}
      </button>
      {state.message && <p>{state.message}</p>}
    </form>
  )
}
```

## useFormStatus

```tsx
'use client'

import { useFormStatus } from 'react-dom'

export function SubmitButton() {
  const { pending } = useFormStatus()
  return (
    <button disabled={pending}>
      {pending ? 'Submitting...' : 'Submit'}
    </button>
  )
}
```
