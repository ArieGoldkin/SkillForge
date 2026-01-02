---
name: db-normalization
description: Database normalization (1NF, 2NF, 3NF) and denormalization
version: 1.0.0
tags: [database, normalization, schema, sql]
size: atomic
domain: backend
---

# Database Normalization

## 1st Normal Form (1NF)

**Rule:** Atomic values, no repeating groups

```sql
-- ❌ Violates 1NF (multiple values in one column)
CREATE TABLE orders (
  id INT PRIMARY KEY,
  product_ids VARCHAR(255)  -- '101,102,103' (bad!)
);

-- ✅ Follows 1NF
CREATE TABLE orders (id INT PRIMARY KEY);

CREATE TABLE order_items (
  id INT PRIMARY KEY,
  order_id INT REFERENCES orders(id),
  product_id INT
);
```

## 2nd Normal Form (2NF)

**Rule:** 1NF + all non-key columns depend on entire primary key

```sql
-- ❌ Violates 2NF (customer_name depends only on customer_id)
CREATE TABLE order_items (
  order_id INT,
  product_id INT,
  customer_name VARCHAR(100),  -- Partial dependency!
  PRIMARY KEY (order_id, product_id)
);

-- ✅ Follows 2NF
CREATE TABLE orders (
  id INT PRIMARY KEY,
  customer_id INT REFERENCES customers(id)
);

CREATE TABLE order_items (
  order_id INT,
  product_id INT,
  quantity INT,
  PRIMARY KEY (order_id, product_id)
);
```

## 3rd Normal Form (3NF)

**Rule:** 2NF + no transitive dependencies

```sql
-- ❌ Violates 3NF (country depends on postal_code)
CREATE TABLE customers (
  id INT PRIMARY KEY,
  postal_code VARCHAR(10),
  country VARCHAR(50)  -- Transitive dependency!
);

-- ✅ Follows 3NF
CREATE TABLE customers (
  id INT PRIMARY KEY,
  postal_code VARCHAR(10) REFERENCES postal_codes(code)
);

CREATE TABLE postal_codes (
  code VARCHAR(10) PRIMARY KEY,
  country VARCHAR(50)
);
```

## When to Denormalize

Denormalize for read-heavy applications:

```sql
-- Denormalized (caching derived data)
CREATE TABLE orders (
  id INT PRIMARY KEY,
  total_amount DECIMAL(10, 2),  -- Pre-calculated
  item_count INT,               -- Pre-calculated
  created_at TIMESTAMP
);
```

**Denormalize when:**
- Read-heavy applications (reporting, analytics)
- Frequently joined tables causing issues
- Pre-calculated aggregates needed
- Performance trumps data integrity
