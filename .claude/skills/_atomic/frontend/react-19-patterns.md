---
name: react-19-patterns
description: React 19 patterns - function declarations, ref as prop, hooks
version: 1.0.0
tags: [react, react-19, patterns, 2025]
size: atomic
domain: frontend
---

# React 19 Patterns

## Function Declarations (No React.FC)

```tsx
// ❌ DEPRECATED
export const Button: React.FC<ButtonProps> = ({ children }) => {
  return <button>{children}</button>
}

// ✅ RECOMMENDED
export function Button({ children }: ButtonProps): React.ReactNode {
  return <button>{children}</button>
}

// ✅ ALSO VALID
export const Button = ({ children }: ButtonProps): React.ReactNode => {
  return <button>{children}</button>
}
```

## Ref as Prop (No forwardRef)

```tsx
// ❌ DEPRECATED
const Input = forwardRef<HTMLInputElement, InputProps>((props, ref) => {
  return <input ref={ref} {...props} />
})

// ✅ RECOMMENDED
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  ref?: React.Ref<HTMLInputElement>
}

export function Input({ ref, ...props }: InputProps): React.ReactNode {
  return <input ref={ref} {...props} />
}
```

## useOptimistic

```tsx
'use client'

import { useOptimistic, useTransition } from 'react'

export function ItemList({ items }: { items: Item[] }) {
  const [optimisticItems, addOptimisticItem] = useOptimistic(
    items,
    (state, newItem: Item) => [...state, newItem]
  )
  const [, startTransition] = useTransition()

  const handleAdd = async (item: Item) => {
    startTransition(() => {
      addOptimisticItem(item)  // Immediate UI update
    })
    await saveItem(item)  // Auto-rollback on error
  }

  return <ul>{optimisticItems.map(i => <li key={i.id}>{i.name}</li>)}</ul>
}
```

## use() Hook

```tsx
import { use } from 'react'

function Comments({ commentsPromise }) {
  const comments = use(commentsPromise)  // Suspends until resolved
  return comments.map(c => <Comment key={c.id} comment={c} />)
}
```

## Context Without Provider

```tsx
// React 19 allows reading context directly
const theme = use(ThemeContext)
```

## Best Practices

- ✅ Use function declarations over React.FC
- ✅ Pass ref as regular prop
- ✅ Use useOptimistic for instant feedback
- ✅ Use useActionState for form state
- ✅ Use useFormStatus in submit buttons
