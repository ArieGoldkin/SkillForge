---
name: db-constraints
description: Database constraints - PK, FK, unique, check, not null
version: 1.0.0
tags: [database, constraints, integrity, sql]
size: atomic
domain: backend
---

# Database Constraints

## Primary Key

```sql
-- Auto-incrementing integer
CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL
);

-- UUID (distributed systems)
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) NOT NULL
);
```

## Foreign Key

```sql
CREATE TABLE orders (
  id INT PRIMARY KEY,
  customer_id INT NOT NULL,
  FOREIGN KEY (customer_id) REFERENCES customers(id)
    ON DELETE CASCADE      -- Delete orders with customer
    ON UPDATE CASCADE      -- Update when customer ID changes
);

-- Alternatives:
ON DELETE RESTRICT   -- Prevent deletion if referenced
ON DELETE SET NULL   -- Set to NULL when parent deleted
ON DELETE NO ACTION  -- Same as RESTRICT
```

## Unique Constraint

```sql
-- Single column
CREATE TABLE users (
  id INT PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL
);

-- Composite unique
CREATE TABLE enrollments (
  student_id INT,
  course_id INT,
  UNIQUE (student_id, course_id)  -- No duplicate enrollments
);
```

## Check Constraint

```sql
CREATE TABLE products (
  id INT PRIMARY KEY,
  price DECIMAL(10, 2) CHECK (price >= 0),
  stock INT CHECK (stock >= 0),
  discount INT CHECK (discount BETWEEN 0 AND 100)
);
```

## Not Null Constraint

```sql
CREATE TABLE users (
  id INT PRIMARY KEY,
  email VARCHAR(255) NOT NULL,     -- Required
  name VARCHAR(100) NOT NULL,      -- Required
  bio TEXT                         -- Optional (nullable)
);
```

## Common Patterns

### One-to-Many

```sql
CREATE TABLE orders (
  id INT PRIMARY KEY,
  customer_id INT NOT NULL REFERENCES customers(id)
);

CREATE TABLE order_items (
  id INT PRIMARY KEY,
  order_id INT NOT NULL REFERENCES orders(id) ON DELETE CASCADE
);
```

### Many-to-Many (Junction Table)

```sql
CREATE TABLE enrollments (
  student_id INT REFERENCES students(id) ON DELETE CASCADE,
  course_id INT REFERENCES courses(id) ON DELETE CASCADE,
  enrolled_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (student_id, course_id)
);
```

### Self-Referencing

```sql
CREATE TABLE employees (
  id INT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  manager_id INT REFERENCES employees(id)
);
```

## Best Practices

- **Always use primary keys**
- **Foreign keys for relationships** - enforce integrity
- **NOT NULL for required fields** - explicit constraints
- **CHECK for business rules** - database-level validation
- **CASCADE carefully** - understand deletion impact
