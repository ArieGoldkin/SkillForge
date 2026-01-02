---
name: zod-validation
description: Zod runtime validation - schemas, safeParse, refinements
version: 1.0.0
tags: [typescript, zod, validation, schemas]
size: atomic
domain: frontend
---

# Zod Validation

## Basic Schema

```typescript
import { z } from 'zod'

const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  age: z.number().int().positive().max(120),
  role: z.enum(['admin', 'user', 'guest']),
  metadata: z.record(z.string()).optional(),
  createdAt: z.date().default(() => new Date())
})

// Infer TypeScript type
type User = z.infer<typeof UserSchema>
```

## Validation

```typescript
// Safe parsing (returns result object)
const result = UserSchema.safeParse(data)
if (result.success) {
  const user: User = result.data
} else {
  console.error(result.error.issues)
}

// Throwing parse (use for known-good data)
const user = UserSchema.parse(data)  // Throws on invalid
```

## Refinements

```typescript
const PasswordSchema = z.string()
  .min(8)
  .refine((pass) => /[A-Z]/.test(pass), 'Must contain uppercase')
  .refine((pass) => /[0-9]/.test(pass), 'Must contain number')
```

## Transforms

```typescript
const EmailSchema = z.string()
  .email()
  .transform(email => email.toLowerCase())
```

## Discriminated Unions

```typescript
const EventSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('click'), x: z.number(), y: z.number() }),
  z.object({ type: z.literal('scroll'), offset: z.number() })
])
```

## Recursive Types

```typescript
interface Category {
  name: string
  children?: Category[]
}

const CategorySchema: z.ZodType<Category> = z.lazy(() =>
  z.object({
    name: z.string(),
    children: z.array(CategorySchema).optional()
  })
)
```

## Best Practices

- ✅ Validate at boundaries (API, forms, external data)
- ✅ Use `.safeParse()` for user input
- ✅ Reuse schemas (don't create inline)
- ✅ Provide clear error messages
