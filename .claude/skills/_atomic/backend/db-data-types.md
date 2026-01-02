---
name: db-data-types
description: SQL data types - strings, numbers, dates, booleans
version: 1.0.0
tags: [database, data-types, sql, schema]
size: atomic
domain: backend
---

# Database Data Types

## String Types

```sql
-- Fixed-length (predictable lengths)
CHAR(10)      -- ISO date: '2025-10-31'
CHAR(2)       -- State code: 'CA'

-- Variable-length
VARCHAR(255)  -- Email, name, short text
TEXT          -- Long text (articles)

-- ✅ Good sizing
email VARCHAR(255)
phone VARCHAR(20)
postal_code VARCHAR(10)

-- ❌ Bad sizing
email VARCHAR(500)       -- Too large
description VARCHAR(50)  -- Too small
```

## Numeric Types

```sql
-- Integers
TINYINT    -- -128 to 127 (age, status)
SMALLINT   -- -32K to 32K (quantities)
INT        -- -2.1B to 2.1B (IDs)
BIGINT     -- Large numbers (timestamps)

-- Decimals
DECIMAL(10, 2)  -- Exact (money: $99,999,999.99)
FLOAT           -- Approximate (scientific)
DOUBLE          -- Higher precision

-- ✅ Use DECIMAL for money
price DECIMAL(10, 2)

-- ❌ Don't use FLOAT for money (rounding errors!)
price FLOAT
```

## Date/Time Types

```sql
DATE       -- 2025-10-31
TIME       -- 14:30:00
DATETIME   -- 2025-10-31 14:30:00
TIMESTAMP  -- Unix timestamp (auto timezone)

-- ✅ Always store UTC
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
```

## Boolean

```sql
-- PostgreSQL
is_active BOOLEAN DEFAULT TRUE

-- MySQL
is_active TINYINT(1) DEFAULT 1
```

## UUID

```sql
-- PostgreSQL
id UUID PRIMARY KEY DEFAULT gen_random_uuid()

-- MySQL
id CHAR(36) PRIMARY KEY DEFAULT (UUID())
```

## JSON

```sql
-- PostgreSQL (use jsonb for indexing)
metadata JSONB DEFAULT '{}'::jsonb

-- MySQL
settings JSON
```

## Best Practices

- **Use smallest type** that fits your data
- **DECIMAL for money** - never FLOAT
- **VARCHAR over TEXT** when you know max length
- **UTC timestamps** - convert in application layer
- **UUID for distributed** systems, INT for single DB
