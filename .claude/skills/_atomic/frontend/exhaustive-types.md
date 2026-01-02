---
name: exhaustive-types
description: assertNever pattern and exhaustive type checking
version: 1.0.0
tags: [typescript, exhaustive, type-safety, patterns]
size: atomic
domain: frontend
---

# Exhaustive Type Checking

## assertNever Pattern

```typescript
function assertNever(x: never): never {
  throw new Error(`Unexpected value: ${x}`)
}

type Status = 'pending' | 'running' | 'completed' | 'failed'

function getStatusColor(status: Status): string {
  switch (status) {
    case 'pending': return 'gray'
    case 'running': return 'blue'
    case 'completed': return 'green'
    case 'failed': return 'red'
    default: return assertNever(status)  // Compile-time check!
  }
}

// Adding 'cancelled' to Status will cause compile error at assertNever
```

## Exhaustive Record Mapping

```typescript
type EventType = 'click' | 'scroll' | 'keypress'

const eventColors = {
  click: 'red',
  scroll: 'blue',
  keypress: 'green',
} as const satisfies Record<EventType, string>

// TypeScript errors if any EventType is missing
```

## Exhaustive Handler Objects

```typescript
type ContentType = 'article' | 'video' | 'podcast'

interface ContentHandler<T> {
  article: (data: ArticleData) => T
  video: (data: VideoData) => T
  podcast: (data: PodcastData) => T
}

function createHandlers<T>(handlers: ContentHandler<T>) {
  return handlers
}

// All content types must be handled
const render = createHandlers({
  article: (data) => <ArticleCard {...data} />,
  video: (data) => <VideoPlayer {...data} />,
  podcast: (data) => <AudioPlayer {...data} />,
})
```

## Anti-Patterns

```typescript
// ❌ NEVER: Non-exhaustive switch
switch (status) {
  case 'pending': return 'gray'
  case 'running': return 'blue'
  // Missing cases!
}

// ❌ NEVER: Default without assertNever
switch (status) {
  case 'pending': return 'gray'
  default: return 'unknown'  // Silent bug if new status added
}

// ❌ NEVER: If-else chains for unions
if (status === 'pending') return 'gray'
else if (status === 'running') return 'blue'
// No compile-time check!
```

## Best Practices

- ✅ Always use `assertNever` in default case
- ✅ Use `satisfies Record<Union, Value>` for mappings
- ✅ Prefer switch over if-else for unions
