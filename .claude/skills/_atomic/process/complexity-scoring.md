---
name: complexity-scoring
description: Task complexity scoring on 1-5 scale
version: 1.0.0
tags: [planning, estimation, complexity, quality-gates]
size: atomic
domain: process
---

# Complexity Scoring (1-5 Scale)

## Level 1: Trivial

- Single file change
- Simple variable rename
- Documentation update
- < 50 lines of code
- < 30 minutes estimated
- No dependencies, no unknowns

## Level 2: Simple

- 1-3 file changes
- Basic function implementation
- Simple CRUD endpoint
- 50-200 lines of code
- 30 min - 2 hours estimated
- 0-1 dependencies

## Level 3: Moderate

- 3-10 file changes
- Multiple component coordination
- API with validation and error handling
- State management integration
- 200-500 lines of code
- 2-8 hours estimated
- 2-3 dependencies
- Some unknowns needing research

## Level 4: Complex

- 10-25 file changes
- Cross-cutting concerns
- Authentication/authorization
- Real-time features (WebSockets)
- Database migrations with data
- 500-1500 lines of code
- 8-24 hours (1-3 days)
- 4-6 dependencies
- Significant unknowns

## Level 5: Very Complex

- 25+ file changes
- Architectural changes
- New service/microservice
- Third-party API integration
- Performance optimization
- 1500+ lines of code
- 24+ hours (3+ days)
- 7+ dependencies
- Many unknowns
- Requires prototyping

## Quick Check

```
1-3 files, < 200 lines, < 2 hours → Level 1-2
3-10 files, 200-500 lines, 2-8 hours → Level 3
10-25 files, 500-1500 lines, 8-24 hours → Level 4
25+ files, 1500+ lines, 24+ hours → Level 5
```
