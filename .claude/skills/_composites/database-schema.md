---
name: database-schema
description: Complete database schema design patterns and best practices
version: 1.0.0
tags: [database, schema, sql, postgresql, design]
size: composite
atomics:
  - backend/db-normalization
  - backend/db-data-types
  - backend/db-indexing
  - backend/db-constraints
  - backend/db-migrations
---

# Database Schema Design Composite

Complete database design knowledge combining normalization, data types, indexing, constraints, and migration patterns.

## When to Use

- Designing new database schemas
- Optimizing query performance with indexes
- Planning schema migrations
- Ensuring data integrity with constraints

## Atomic Skills

### 1. Normalization (`db-normalization`)
1NF, 2NF, 3NF and when to denormalize for performance.

### 2. Data Types (`db-data-types`)
Choosing appropriate types: strings, numbers, dates, JSON, UUID.

### 3. Indexing (`db-indexing`)
B-tree, hash, full-text, composite index strategies.

### 4. Constraints (`db-constraints`)
Primary keys, foreign keys, unique, check, not null.

### 5. Migrations (`db-migrations`)
Zero-downtime patterns, Alembic usage, reversible migrations.

## Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│  DATABASE DESIGN DECISION TREE                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Money values? ──► DECIMAL(10,2) (never FLOAT!)             │
│  IDs? ──► UUID (distributed) or INT (single DB)             │
│  Timestamps? ──► TIMESTAMPTZ in UTC                         │
│                                                             │
│  Slow queries? ──► Check EXPLAIN, add indexes               │
│  Foreign keys? ──► Always index them                        │
│  WHERE columns? ──► Index frequently queried                │
│                                                             │
│  Adding column? ──► Nullable first, backfill, then NOT NULL │
│  Dropping column? ──► Stop writes → stop reads → drop       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## SkillForge Patterns

```python
# Standard table pattern
class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)

    # Always index tenant_id for multi-tenant queries
    __table_args__ = (
        Index("ix_documents_tenant_id", "tenant_id"),
        Index("ix_documents_user_id", "user_id"),
    )
```

## Load Order

1. Start with `db-normalization` for schema structure
2. Apply `db-data-types` for column definitions
3. Add `db-constraints` for data integrity
4. Optimize with `db-indexing` for performance
5. Use `db-migrations` for deployment
