---
name: db-indexing
description: Database indexing strategies - B-tree, hash, composite
version: 1.0.0
tags: [database, indexing, performance, sql]
size: atomic
domain: backend
---

# Database Indexing

## When to Create Indexes

```sql
-- ✅ Index foreign keys
CREATE INDEX idx_orders_customer_id ON orders(customer_id);

-- ✅ Index frequently queried columns
CREATE INDEX idx_users_email ON users(email);

-- ✅ Index WHERE, ORDER BY, GROUP BY columns
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- ✅ Composite index for multi-column queries
CREATE INDEX idx_orders_customer_status ON orders(customer_id, status);
```

## Index Types

### B-Tree (Default)

```sql
-- Best for equality and range queries
CREATE INDEX idx_products_price ON products(price);

-- Benefits:
SELECT * FROM products WHERE price > 100;
SELECT * FROM products WHERE price BETWEEN 50 AND 150;
```

### Hash Index

```sql
-- Best for exact matches only
CREATE INDEX idx_users_email USING HASH ON users(email);

-- Benefits:
SELECT * FROM users WHERE email = 'user@example.com';
-- Does NOT benefit range queries
```

### Full-Text Index

```sql
-- Best for text search
CREATE FULLTEXT INDEX idx_articles_content ON articles(title, content);

-- Usage:
SELECT * FROM articles
WHERE MATCH(title, content) AGAINST('database design');
```

### Partial Index (PostgreSQL)

```sql
-- Index only specific rows
CREATE INDEX idx_active_users ON users(email)
WHERE is_active = TRUE;
```

## Composite Index Order

**Column order matters!**

```sql
CREATE INDEX idx_orders_customer_status ON orders(customer_id, status);

-- ✅ Uses index (left-to-right)
WHERE customer_id = 123 AND status = 'pending'
WHERE customer_id = 123

-- ❌ Doesn't use index (status is second)
WHERE status = 'pending'
```

**Rule:** Put most selective column first

## Analyze Queries

```sql
EXPLAIN SELECT * FROM orders WHERE customer_id = 123;
```

**Look for:**
- **Type:** ALL (bad) → index/ref (good)
- **Key:** Index actually used
- **Rows:** Estimated rows scanned

## Best Practices

- **Index foreign keys** - always
- **Index WHERE columns** - frequently queried
- **Avoid over-indexing** - slows writes
- **Composite indexes** - match query patterns
- **EXPLAIN queries** - verify index usage
