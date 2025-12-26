# React 19 Component Patterns

## Overview

React 19 introduces breaking changes to component declaration patterns. This reference provides migration guidance and best practices for 2025+ React development.

---

## 1. React.FC Removal

### Why React.FC is Deprecated

React 18's `React.FC<Props>` automatically included `children` in the props type:

```typescript
// React 18: children was implicit
type FC<P = {}> = FunctionComponent<P>
interface FunctionComponent<P = {}> {
  (props: P & { children?: ReactNode }): ReactNode | null
  // ...
}
```

React 19 removes this implicit `children`, making `React.FC` misleading and unnecessary.

### Migration Pattern

```typescript
// ═══════════════════════════════════════════════════════════════════════════
// BEFORE (React 18)
// ═══════════════════════════════════════════════════════════════════════════

import React from 'react'

interface ButtonProps {
  variant: 'primary' | 'secondary'
  onClick: () => void
}

export const Button: React.FC<ButtonProps> = ({ variant, onClick, children }) => {
  return (
    <button className={`btn-${variant}`} onClick={onClick}>
      {children}
    </button>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// AFTER (React 19)
// ═══════════════════════════════════════════════════════════════════════════

interface ButtonProps {
  variant: 'primary' | 'secondary'
  onClick: () => void
  children: React.ReactNode  // Explicit when needed
}

export function Button({ variant, onClick, children }: ButtonProps): React.ReactNode {
  return (
    <button className={`btn-${variant}`} onClick={onClick}>
      {children}
    </button>
  )
}
```

### Components Without Children

```typescript
// When component has no children, don't include it in props
interface StatusBadgeProps {
  status: 'active' | 'inactive'
  count: number
}

export function StatusBadge({ status, count }: StatusBadgeProps): React.ReactNode {
  return (
    <span className={`badge-${status}`}>
      {count}
    </span>
  )
}
```

### Regex for Bulk Migration

Use this regex pattern to find React.FC usage:

```bash
# Find all React.FC patterns
grep -rn "React\.FC<\|: FC<\|React\.FunctionComponent" --include="*.tsx" src/

# Count occurrences
grep -c "React\.FC<" --include="*.tsx" -r src/
```

---

## 2. forwardRef Removal

### Why forwardRef is Deprecated

React 19 allows `ref` to be passed as a regular prop, eliminating the need for `forwardRef`:

```typescript
// ═══════════════════════════════════════════════════════════════════════════
// BEFORE (React 18)
// ═══════════════════════════════════════════════════════════════════════════

import { forwardRef } from 'react'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, ...props }, ref) => {
    return (
      <div>
        <label>{label}</label>
        <input ref={ref} {...props} />
      </div>
    )
  }
)

Input.displayName = 'Input'

// ═══════════════════════════════════════════════════════════════════════════
// AFTER (React 19)
// ═══════════════════════════════════════════════════════════════════════════

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string
  ref?: React.Ref<HTMLInputElement>
}

export function Input({ label, ref, ...props }: InputProps): React.ReactNode {
  return (
    <div>
      <label>{label}</label>
      <input ref={ref} {...props} />
    </div>
  )
}
```

### Complex Ref Patterns

For components that need ref callbacks or imperative handles:

```typescript
interface DialogProps {
  title: string
  children: React.ReactNode
  ref?: React.Ref<HTMLDialogElement>
}

export function Dialog({ title, children, ref }: DialogProps): React.ReactNode {
  return (
    <dialog ref={ref}>
      <h2>{title}</h2>
      {children}
    </dialog>
  )
}

// Usage
function App() {
  const dialogRef = useRef<HTMLDialogElement>(null)

  return (
    <Dialog ref={dialogRef} title="Confirm">
      <p>Are you sure?</p>
      <button onClick={() => dialogRef.current?.close()}>Cancel</button>
    </Dialog>
  )
}
```

---

## 3. New React 19 Hooks

### useActionState

Replaces the experimental `useFormState`. Manages form state with server actions:

```typescript
'use client'

import { useActionState } from 'react'

type FormState = {
  message: string
  errors: Record<string, string[]>
  success: boolean
}

const initialState: FormState = {
  message: '',
  errors: {},
  success: false
}

async function createUser(
  prevState: FormState,
  formData: FormData
): Promise<FormState> {
  const email = formData.get('email') as string
  const name = formData.get('name') as string

  // Validation
  if (!email.includes('@')) {
    return {
      message: 'Validation failed',
      errors: { email: ['Invalid email format'] },
      success: false
    }
  }

  // Server mutation
  try {
    await db.user.create({ data: { email, name } })
    return { message: 'User created!', errors: {}, success: true }
  } catch (error) {
    return { message: 'Failed to create user', errors: {}, success: false }
  }
}

export function CreateUserForm(): React.ReactNode {
  const [state, formAction, isPending] = useActionState(createUser, initialState)

  return (
    <form action={formAction}>
      <input name="name" placeholder="Name" disabled={isPending} />
      <input name="email" placeholder="Email" disabled={isPending} />

      {state.errors.email && (
        <span className="error">{state.errors.email[0]}</span>
      )}

      <button type="submit" disabled={isPending}>
        {isPending ? 'Creating...' : 'Create User'}
      </button>

      {state.message && (
        <p className={state.success ? 'success' : 'error'}>
          {state.message}
        </p>
      )}
    </form>
  )
}
```

### useFormStatus

For submit buttons that need form state without prop drilling:

```typescript
'use client'

import { useFormStatus } from 'react-dom'

interface SubmitButtonProps {
  children: React.ReactNode
  loadingText?: string
}

export function SubmitButton({
  children,
  loadingText = 'Submitting...'
}: SubmitButtonProps): React.ReactNode {
  const { pending, data, method, action } = useFormStatus()

  return (
    <button
      type="submit"
      disabled={pending}
      aria-busy={pending}
      aria-disabled={pending}
    >
      {pending ? loadingText : children}
    </button>
  )
}

// Usage - no props needed!
function ContactForm() {
  return (
    <form action={submitContactForm}>
      <input name="message" />
      <SubmitButton>Send Message</SubmitButton>
    </form>
  )
}
```

### useOptimistic

For instant UI updates with automatic rollback on error:

```typescript
'use client'

import { useOptimistic, useTransition } from 'react'

interface Todo {
  id: string
  text: string
  completed: boolean
}

interface TodoListProps {
  todos: Todo[]
  onToggle: (id: string) => Promise<void>
}

export function TodoList({ todos, onToggle }: TodoListProps): React.ReactNode {
  const [optimisticTodos, setOptimisticTodo] = useOptimistic(
    todos,
    (state, updatedTodo: Todo) =>
      state.map(todo =>
        todo.id === updatedTodo.id ? updatedTodo : todo
      )
  )
  const [, startTransition] = useTransition()

  const handleToggle = async (todo: Todo) => {
    // Immediately update UI
    startTransition(() => {
      setOptimisticTodo({ ...todo, completed: !todo.completed })
    })

    // Server mutation - auto rollback on error
    await onToggle(todo.id)
  }

  return (
    <ul>
      {optimisticTodos.map(todo => (
        <li key={todo.id}>
          <input
            type="checkbox"
            checked={todo.completed}
            onChange={() => handleToggle(todo)}
          />
          <span className={todo.completed ? 'completed' : ''}>
            {todo.text}
          </span>
        </li>
      ))}
    </ul>
  )
}
```

---

## 4. Testing React 19 Components

### Testing Function Declaration Components

```typescript
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'

import { Button } from './Button'

describe('Button', () => {
  it('renders children correctly', () => {
    render(<Button variant="primary" onClick={() => {}}>Click me</Button>)
    expect(screen.getByText('Click me')).toBeInTheDocument()
  })

  it('applies variant class', () => {
    render(<Button variant="secondary" onClick={() => {}}>Test</Button>)
    expect(screen.getByRole('button')).toHaveClass('btn-secondary')
  })
})
```

### Testing Hooks with renderHook

```typescript
import { renderHook, act, waitFor } from '@testing-library/react'
import * as React from 'react'
import { describe, it, expect, vi } from 'vitest'

import { useLibrarySearch } from './useLibrarySearch'

// Create wrapper for providers
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children
    )
  }
}

describe('useLibrarySearch', () => {
  it('returns search results', async () => {
    const { result } = renderHook(
      () => useLibrarySearch({ query: 'react' }),
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toHaveLength(10)
  })
})
```

---

## 5. Migration Checklist

### Component Declaration Migration

- [ ] Search for `React.FC<` patterns
- [ ] Replace with function declarations
- [ ] Add explicit `children: React.ReactNode` to props when needed
- [ ] Add explicit return type `: React.ReactNode`
- [ ] Remove React import if only used for FC type
- [ ] Run TypeScript to verify no type errors

### forwardRef Migration

- [ ] Search for `forwardRef<` patterns
- [ ] Add `ref?: React.Ref<ElementType>` to props interface
- [ ] Destructure `ref` from props instead of second parameter
- [ ] Remove `forwardRef` wrapper
- [ ] Remove `.displayName` assignments (no longer needed)
- [ ] Test ref forwarding still works

### Hooks Migration

- [ ] Replace `useFormState` with `useActionState`
- [ ] Add `useFormStatus` to submit buttons (remove isPending prop drilling)
- [ ] Add `useOptimistic` for optimistic updates (remove manual rollback logic)
- [ ] Wrap optimistic updates in `startTransition`

---

## 6. ESLint Rules

Add these ESLint rules to enforce React 19 patterns:

```json
{
  "rules": {
    "@typescript-eslint/ban-types": [
      "error",
      {
        "types": {
          "React.FC": {
            "message": "Use function declarations instead. See react-19-patterns.md",
            "fixWith": "function Component(props: Props): React.ReactNode"
          },
          "React.FunctionComponent": {
            "message": "Use function declarations instead. See react-19-patterns.md"
          }
        }
      }
    ]
  }
}
```

---

**Last Updated**: 2025-12-26
**React Version**: 19.0.0
**SkillForge Modernization Commit**: 827c323e
