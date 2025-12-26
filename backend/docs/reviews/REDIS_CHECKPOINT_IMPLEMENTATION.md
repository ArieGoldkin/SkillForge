# Redis Checkpointing Implementation

**Issue**: #576 (GAP 3 - Redis Checkpoint Support)
**Date**: 2025-12-26
**Status**: ✅ Implemented

## Overview

Added Redis checkpointing support for LangGraph workflows to enable distributed checkpointing across multiple backend instances with automatic TTL-based cleanup.

## Changes Made

### 1. Configuration Updates (`app/core/config.py`)

Added two new configuration fields:

```python
USE_REDIS_CHECKPOINT: bool = Field(
    default=False,
    description=(
        "Use Redis for LangGraph checkpointing instead of PostgreSQL. "
        "Enables distributed checkpointing across multiple backend instances "
        "with automatic TTL-based cleanup. When disabled, uses PostgreSQL checkpointing."
    ),
)
REDIS_CHECKPOINT_TTL: int = Field(
    default=3600,
    description=(
        "TTL in seconds for Redis checkpoints (default: 1 hour). "
        "Checkpoints are automatically cleaned up after this duration. "
        "Set higher for long-running workflows or debugging."
    ),
)
```

### 2. Graph Builder Updates (`app/domains/analysis/workflows/graph_builder.py`)

Enhanced `_get_checkpointer()` function to support Redis:

**Checkpointer Selection Priority:**
1. **MemorySaver** - For tests (when `PYTEST_CURRENT_TEST` is set)
2. **RedisSaver** - If `USE_REDIS_CHECKPOINT=true` and `REDIS_URL` is set
3. **PostgresSaver** - If `DATABASE_URL` is set
4. **MemorySaver** - As fallback (development/local mode)

**Implementation Details:**
```python
# Try RedisSaver if enabled and configured
if settings.USE_REDIS_CHECKPOINT and settings.REDIS_URL and RedisSaver is not None:
    try:
        # RedisSaver expects TTL in minutes via "default_ttl" key
        # Convert seconds to minutes for RedisSaver
        ttl_minutes = settings.REDIS_CHECKPOINT_TTL / 60.0
        checkpointer = RedisSaver.from_conn_string(
            settings.REDIS_URL,
            ttl={"default_ttl": ttl_minutes},
        )
        logger.info(
            "workflow_checkpointer_initialized",
            type="RedisSaver",
            ttl_seconds=settings.REDIS_CHECKPOINT_TTL,
            ttl_minutes=ttl_minutes,
            redis_url=settings.REDIS_URL.split("@")[-1],
        )
        return checkpointer
    except (ValueError, ConnectionError) as e:
        logger.warning(
            "workflow_checkpointer_fallback_from_redis",
            error=str(e),
            fallback="PostgresSaver or MemorySaver",
        )
        # Fall through to PostgresSaver/MemorySaver
```

**Note**: The `REDIS_CHECKPOINT_TTL` configuration is in **seconds** (user-friendly), but RedisSaver expects TTL in **minutes** via the `{"default_ttl": X}` dict format. The code automatically converts seconds to minutes.

## Benefits

### Redis Checkpointing Benefits
- **Distributed checkpointing** across multiple backend instances
- **Automatic TTL-based cleanup** (no manual garbage collection needed)
- **Better horizontal scaling** for high-concurrency workflows
- **Isolated checkpoint storage** (doesn't compete with application data)

### PostgreSQL Checkpointing Benefits
- **Single source of truth** (same DB as application data)
- **Simpler deployment** (no Redis dependency)
- **Persistent checkpoints** (no TTL expiration)
- **Transactional consistency** with application data

## Configuration Examples

### Development (Default - MemorySaver)
```bash
# .env
# No configuration needed - uses MemorySaver by default
```

### Production with Redis Checkpointing
```bash
# .env
USE_REDIS_CHECKPOINT=true
REDIS_URL=redis://redis.example.com:6379
REDIS_CHECKPOINT_TTL=3600  # 1 hour (default)
```

### Production with PostgreSQL Checkpointing
```bash
# .env
USE_REDIS_CHECKPOINT=false  # or omit (default is false)
DATABASE_URL=postgresql://user:pass@db.example.com/skillforge
```

### Long-Running Workflows (Extended TTL)
```bash
# .env
USE_REDIS_CHECKPOINT=true
REDIS_URL=redis://redis.example.com:6379
REDIS_CHECKPOINT_TTL=7200  # 2 hours for long workflows
```

## Testing

### Unit Tests
No new unit tests required - existing tests continue to use `MemorySaver` (controlled by `PYTEST_CURRENT_TEST` environment variable).

### Manual Testing
```bash
# Start Redis
docker compose up -d redis

# Enable Redis checkpointing
export USE_REDIS_CHECKPOINT=true
export REDIS_URL=redis://localhost:6380
export REDIS_CHECKPOINT_TTL=3600

# Start backend
poetry run uvicorn app.main:app --reload

# Trigger analysis and verify checkpoints in Redis
redis-cli -p 6380
> KEYS checkpoint:*
> TTL checkpoint:<thread_id>:<checkpoint_ns>
```

### Verification Checklist
- ✅ RedisSaver used when `USE_REDIS_CHECKPOINT=true`
- ✅ PostgresSaver used when `USE_REDIS_CHECKPOINT=false`
- ✅ MemorySaver used in tests
- ✅ Graceful fallback on Redis connection errors
- ✅ Checkpoints have correct TTL set
- ✅ Structured logging includes checkpointer type and TTL

## Migration Path

### From PostgreSQL to Redis Checkpointing
1. Deploy Redis instance (or use existing one)
2. Update `.env`:
   ```bash
   USE_REDIS_CHECKPOINT=true
   REDIS_URL=redis://redis.example.com:6379
   REDIS_CHECKPOINT_TTL=3600
   ```
3. Restart backend instances
4. **Note**: Existing PostgreSQL checkpoints will not be migrated. In-flight workflows will restart from scratch.

### From Redis to PostgreSQL Checkpointing
1. Update `.env`:
   ```bash
   USE_REDIS_CHECKPOINT=false
   ```
2. Restart backend instances
3. **Note**: Redis checkpoints will expire after TTL. In-flight workflows will restart from scratch.

## Performance Considerations

### Redis Checkpointing
- **Pros**: Fast read/write, automatic cleanup, distributed access
- **Cons**: Additional Redis dependency, checkpoints expire after TTL
- **Best for**: High-concurrency, distributed deployments, short-lived workflows

### PostgreSQL Checkpointing
- **Pros**: Single database, persistent storage, transactional
- **Cons**: Slower than Redis, requires manual cleanup (garbage collection)
- **Best for**: Single-instance deployments, long-lived workflows, debugging

## Known Limitations

1. **No checkpoint migration**: Switching between Redis/PostgreSQL requires workflows to restart
2. **TTL expiration**: Redis checkpoints expire after TTL (configurable)
3. **No cross-backend compatibility**: Cannot mix Redis and PostgreSQL checkpoints

## Dependencies

- `langgraph-checkpoint-redis>=0.3.1` (already installed in `pyproject.toml`)
- Redis server (when `USE_REDIS_CHECKPOINT=true`)

## Code Quality

All code quality checks passed:
- ✅ `ruff format --check` - Formatting correct
- ✅ `ruff check` - Linting passed
- ✅ `ty check` - Type checking passed

## Related Issues

- #576 - Redis Checkpoint Support (GAP 3)
- #444 - Event Broadcaster Redis Backend (similar Redis integration pattern)

## Future Enhancements

1. **Checkpoint migration tool**: Migrate checkpoints between Redis/PostgreSQL
2. **Hybrid checkpointing**: Use Redis for hot checkpoints, PostgreSQL for cold storage
3. **Checkpoint compression**: Reduce Redis memory usage for large workflows
4. **Checkpoint metrics**: Monitor checkpoint size, access patterns, TTL expiration

## References

- [LangGraph Checkpointing Docs](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [langgraph-checkpoint-redis](https://github.com/langchain-ai/langgraph-checkpoint-redis)
- [Redis TTL Documentation](https://redis.io/commands/ttl/)
