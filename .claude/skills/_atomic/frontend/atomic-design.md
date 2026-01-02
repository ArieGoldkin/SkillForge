---
name: atomic-design
description: Atomic design methodology - atoms, molecules, organisms
version: 1.0.0
tags: [design-system, components, architecture]
size: atomic
domain: frontend
---

# Atomic Design

**Atoms** → **Molecules** → **Organisms** → **Templates** → **Pages**

## Atoms (Primitives)

Basic building blocks:

```typescript
// Button atom
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  children: React.ReactNode
}
```

Examples: Button, Input, Label, Icon, Badge, Avatar

## Molecules (Simple Compositions)

Groups of atoms:

```typescript
// FormField molecule = Label + Input + ErrorMessage
interface FormFieldProps {
  label: string
  name: string
  error?: string
  required?: boolean
  children: React.ReactNode
}
```

Examples: SearchBar, FormField, Card

## Organisms (Complex Compositions)

Complex UI from molecules and atoms:

```typescript
// Navigation organism
<Navigation>
  <Logo />
  <NavLinks />
  <SearchBar />
  <UserMenu />
</Navigation>
```

Examples: Navigation, ProductGrid, UserProfile, Modal

## Templates (Layouts)

Page-level structures:

```typescript
// Dashboard template
<DashboardLayout>
  <Sidebar />
  <Header />
  <MainContent>{children}</MainContent>
</DashboardLayout>
```

## Pages

Templates with real content:

```typescript
<DashboardLayout>
  <AnalyticsDashboard data={analytics} />
</DashboardLayout>
```

## Composition Pattern

```tsx
// Compound component pattern
<Card>
  <Card.Header>
    <Card.Title>Title</Card.Title>
  </Card.Header>
  <Card.Body>Content</Card.Body>
  <Card.Footer>Actions</Card.Footer>
</Card>
```

## Best Practices

- ✅ Start with atoms, build up
- ✅ Keep atoms truly atomic
- ✅ Use composition over configuration
- ✅ Document each level
