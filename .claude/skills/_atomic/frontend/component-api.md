---
name: component-api
description: Component API patterns - props, polymorphic, composition
version: 1.0.0
tags: [react, components, api-design, typescript]
size: atomic
domain: frontend
---

# Component API Design

## Predictable Props

```typescript
// ✅ Consistent naming
<Button variant="primary" size="md" />
<Input variant="outlined" size="md" />

// ❌ Inconsistent
<Button type="primary" sizeMode="md" />
<Input style="outlined" inputSize="md" />
```

## Sensible Defaults

```typescript
// ✅ Provides defaults
interface ButtonProps {
  variant?: 'primary' | 'secondary'  // Default: primary
  size?: 'sm' | 'md' | 'lg'          // Default: md
}

// ❌ Everything required
interface ButtonProps {
  variant: 'primary' | 'secondary'
  size: 'sm' | 'md' | 'lg'
  color: string
  padding: string
}
```

## Composition Over Configuration

```tsx
// ✅ Composable
<Card>
  <Card.Header>
    <Card.Title>Title</Card.Title>
  </Card.Header>
  <Card.Body>Content</Card.Body>
</Card>

// ❌ Too many props
<Card
  title="Title"
  content="Content"
  hasHeader={true}
/>
```

## Polymorphic Components

```typescript
interface ButtonProps<T extends React.ElementType = 'button'> {
  as?: T
  children: React.ReactNode
}

type Props<T extends React.ElementType> = ButtonProps<T> &
  Omit<React.ComponentPropsWithoutRef<T>, keyof ButtonProps<T>>

function Button<T extends React.ElementType = 'button'>({
  as,
  children,
  ...props
}: Props<T>) {
  const Component = as || 'button'
  return <Component {...props}>{children}</Component>
}

// Usage
<Button as="a" href="/login">Login</Button>
<Button onClick={handleClick}>Click Me</Button>
```

## Children Pattern

```typescript
// Accept ReactNode for flexibility
interface ContainerProps {
  children: React.ReactNode
  className?: string
}
```

## Best Practices

- ✅ Use consistent prop names
- ✅ Provide sensible defaults
- ✅ Prefer composition
- ✅ Use polymorphic for flexibility
- ❌ Avoid prop drilling
