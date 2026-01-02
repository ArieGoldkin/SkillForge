---
name: review-checklist
description: Code review checklists for quality, security, and testing
version: 1.0.0
tags: [code-review, checklist, quality, security]
size: atomic
domain: process
---

# Review Checklists

## General Code Quality

- [ ] **Readability**: Easy to understand
- [ ] **Naming**: Clear, descriptive names
- [ ] **DRY**: No unnecessary duplication
- [ ] **Function Size**: < 50 lines
- [ ] **Complexity**: Cyclomatic < 10

## Functionality

- [ ] **Correctness**: Does what it's supposed to
- [ ] **Edge Cases**: Null, empty, min/max handled
- [ ] **Error Handling**: Errors caught appropriately
- [ ] **Input Validation**: User input validated

## Testing

- [ ] **Coverage**: New code has tests
- [ ] **Quality**: Tests test the right things
- [ ] **Edge Cases**: Boundary conditions covered
- [ ] **Isolation**: Tests don't depend on each other

## Performance

- [ ] **N+1 Queries**: Avoided with eager loading
- [ ] **Caching**: Used where appropriate
- [ ] **Algorithm**: No O(n²) when O(n) possible
- [ ] **Resource Cleanup**: Files, connections released

## Security

- [ ] **Authentication**: Protected endpoints require auth
- [ ] **Authorization**: Users access only their data
- [ ] **Input Sanitization**: SQL/XSS injection prevented
- [ ] **Secrets**: No hardcoded credentials
- [ ] **HTTPS**: Production uses TLS

## TypeScript/JavaScript

- [ ] **Type Safety**: No `any` types
- [ ] **Async/Await**: Promises handled correctly
- [ ] **Null Checks**: `?.` operator where needed
- [ ] **Const vs Let**: Const for immutable

## Python

- [ ] **PEP 8**: Style guide followed
- [ ] **Type Hints**: Functions annotated
- [ ] **Context Managers**: Using `with` for files
- [ ] **Specific Exceptions**: Not bare `except:`

## Database

- [ ] **Migrations**: Schema changes have migrations
- [ ] **Indexes**: Appropriate indexes created
- [ ] **Foreign Keys**: Constraints defined
