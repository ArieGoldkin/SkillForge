---
name: db-migrations
description: Database migration patterns and zero-downtime strategies
version: 1.0.0
tags: [database, migrations, alembic, schema-changes]
size: atomic
domain: backend
---

# Database Migrations

## Migration Best Practices

### 1. Always Reversible

```sql
-- Up migration
ALTER TABLE users ADD COLUMN phone VARCHAR(20);

-- Down migration
ALTER TABLE users DROP COLUMN phone;
```

### 2. Backward Compatible

```sql
-- ❌ Bad: Add required column (breaks existing code)
ALTER TABLE users ADD COLUMN middle_name VARCHAR(50) NOT NULL;

-- ✅ Good: Add nullable first
ALTER TABLE users ADD COLUMN middle_name VARCHAR(50);

-- Later: Populate then make required
UPDATE users SET middle_name = '' WHERE middle_name IS NULL;
ALTER TABLE users MODIFY COLUMN middle_name VARCHAR(50) NOT NULL;
```

### 3. Separate Data from Schema

```sql
-- Migration 1: Schema change
ALTER TABLE orders ADD COLUMN status VARCHAR(20) DEFAULT 'pending';

-- Migration 2: Data migration
UPDATE orders SET status = 'completed' WHERE completed_at IS NOT NULL;
```

## Zero-Downtime Patterns

### Adding a Column

```sql
-- Step 1: Add nullable column
ALTER TABLE users ADD COLUMN phone VARCHAR(20);

-- Step 2: Deploy code that writes to new column
-- Step 3: Backfill existing rows
UPDATE users SET phone = old_phone WHERE phone IS NULL;

-- Step 4: Make required (if needed)
ALTER TABLE users MODIFY COLUMN phone VARCHAR(20) NOT NULL;
```

### Renaming a Column

```sql
-- Step 1: Add new column
ALTER TABLE users ADD COLUMN email_address VARCHAR(255);

-- Step 2: Copy data
UPDATE users SET email_address = email;

-- Step 3: Deploy code reading new column
-- Step 4: Deploy code writing new column
-- Step 5: Drop old column
ALTER TABLE users DROP COLUMN email;
```

### Dropping a Column

```sql
-- Step 1: Deploy code that doesn't read column
-- Step 2: Deploy code that doesn't write column
-- Step 3: Drop column
ALTER TABLE users DROP COLUMN deprecated_field;
```

## Alembic Pattern

```python
"""add phone column to users

Revision ID: abc123
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('users', sa.Column('phone', sa.String(20)))

def downgrade():
    op.drop_column('users', 'phone')
```

## Testing Migrations

```bash
# Test on staging with production data
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# Measure duration
time alembic upgrade head
```

## Best Practices

- **Test on production copy** before deploying
- **Measure migration duration** - plan for downtime
- **Small, incremental changes** - easier rollback
- **Never delete data** without backup
- **Document breaking changes** in migration message
