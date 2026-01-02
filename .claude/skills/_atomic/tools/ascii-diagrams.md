---
name: ascii-diagrams
description: ASCII art for architecture diagrams and workflows
version: 1.0.0
tags: [ascii, visualization, diagrams, architecture]
size: atomic
domain: tools
---

# ASCII Diagrams

## Box-Drawing Characters

```
┌─┐│└─┘  Standard weight
┏━┓┃┗━┛  Heavy weight
├─┤┬┴    Connectors
╔═╗║╚═╝  Double lines
▶ ◀ ▼ ▲  Arrows
```

## Architecture Pattern

```
┌──────────────┐      ┌──────────────┐
│   Frontend   │─────▶│   Backend    │
│   React 19   │      │   FastAPI    │
└──────────────┘      └───────┬──────┘
                              │
                              ▼
                      ┌──────────────┐
                      │  PostgreSQL  │
                      └──────────────┘
```

## Flow Pattern

```
Request ──▶ [Auth] ──▶ [Validate] ──▶ [Process] ──▶ Response
               │           │             │
               ▼           ▼             ▼
            Reject      Reject        Database
```

## Progress Pattern

```
[████████░░] 80% Complete

✅ Design    (2 days)
✅ Backend   (5 days)
🔄 Frontend  (3 days)
⏳ Testing   (pending)
```

## Decision Tree

```
┌─────────────────────────────────────┐
│  DECISION TREE                      │
├─────────────────────────────────────┤
│                                     │
│  Need state? ──► Redux/Zustand      │
│  Simple CRUD? ──► REST API          │
│  Complex queries? ──► GraphQL       │
│                                     │
└─────────────────────────────────────┘
```

## Table Pattern

```
┌──────────┬───────────┬────────┐
│ Status   │ Count     │ %      │
├──────────┼───────────┼────────┤
│ Passed   │ 45        │ 90%    │
│ Failed   │ 3         │ 6%     │
│ Skipped  │ 2         │ 4%     │
└──────────┴───────────┴────────┘
```

## Layer Diagram

```
┌─────────────────────────────────────┐
│  Layer 0: EDGE        │  WAF       │
├─────────────────────────────────────┤
│  Layer 1: GATEWAY     │  JWT       │
├─────────────────────────────────────┤
│  Layer 2: INPUT       │  Validate  │
├─────────────────────────────────────┤
│  Layer 3: AUTH        │  RBAC      │
└─────────────────────────────────────┘
```
