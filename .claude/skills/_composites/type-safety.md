---
name: type-safety
description: End-to-end type safety with Zod, tRPC, and exhaustive patterns
version: 1.0.0
tags: [typescript, zod, trpc, type-safety, validation]
size: composite
atomics:
  - frontend/zod-validation
  - frontend/trpc-api
  - frontend/exhaustive-types
  - frontend/branded-types
---

# Type Safety Composite

End-to-end type safety from database to UI.

## When to Use

- Building type-safe APIs
- Validating user input
- Preventing ID type mixing
- Ensuring exhaustive handling

## Atomic Skills

### 1. Zod Validation (`zod-validation`)
Runtime schemas, safeParse, refinements, transforms.

### 2. tRPC API (`trpc-api`)
Type-safe procedures, React Query integration.

### 3. Exhaustive Types (`exhaustive-types`)
assertNever pattern, exhaustive records.

### 4. Branded Types (`branded-types`)
Type-safe IDs with Zod brand and Python NewType.

## Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│  TYPE SAFETY DECISION TREE                                  │
├─────────────────────────────────────────────────────────────┤
│  User input? ──► Zod safeParse()                            │
│  API endpoints? ──► tRPC procedures                         │
│  Switch on union? ──► assertNever in default                │
│  Entity IDs? ──► Branded types                              │
│                                                             │
│  TypeScript IDs? ──► z.string().uuid().brand<'UserId'>()    │
│  Python IDs? ──► NewType("UserId", UUID)                    │
└─────────────────────────────────────────────────────────────┘
```

## Load Order

1. `zod-validation` - Runtime validation foundation
2. `trpc-api` - Type-safe API layer
3. `exhaustive-types` - Compile-time safety
4. `branded-types` - ID type safety
