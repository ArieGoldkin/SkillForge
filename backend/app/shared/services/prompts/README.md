# Langfuse Prompt Management

**Issue #379**: Centralized prompt management with Langfuse integration, multi-level caching, and offline fallback.

## Overview

The Prompt Management system provides:
- **Version control** for prompts without code deploys
- **A/B testing** infrastructure for prompt experiments
- **Multi-level caching** for performance (L1 LRU + L2 Redis)
- **Offline operation** with hardcoded fallbacks
- **Trace attribution** to track which prompt version was used

## Architecture

```
Application → PromptManager.get_prompt()
                ↓
            L1 Cache (In-memory LRU, 5 min TTL)
                ↓ MISS
            L2 Cache (Redis, 15 min TTL)
                ↓ MISS
            L3 Source (Langfuse API)
                ↓ FAILURE
            Fallback (Hardcoded prompts)
```

## Configuration

Add to `.env`:

```bash
# Langfuse Prompt Management (Issue #379)
LANGFUSE_PROMPTS_ENABLED=false           # Gradual rollout
LANGFUSE_PROMPTS_L1_TTL=300              # 5 minutes
LANGFUSE_PROMPTS_L2_TTL=900              # 15 minutes
LANGFUSE_PROMPTS_REDIS_ENABLED=true      # Shared cache across workers
```

## Usage

### Basic Usage

```python
from app.shared.services.prompts import get_prompt_manager

# Get manager instance (singleton)
prompt_manager = get_prompt_manager()

# Fetch and compile prompt
prompt = await prompt_manager.get_prompt(
    name="analysis-supervisor-routing",
    variables={"agent_list": agent_list_str},
    label="production",
)

# Get metadata for trace attribution
metadata = await prompt_manager.get_prompt_metadata(
    name="analysis-supervisor-routing",
    label="production",
)

# Use metadata in traces
logger.info(
    "prompt_used",
    prompt_source=metadata["prompt_source"],
    prompt_version=metadata["prompt_version"],
)
```

### Supervisor Migration (Phase 2)

The supervisor node now uses PromptManager:

```python
# In supervisor.py
from app.shared.services.prompts import get_prompt_manager
from app.domains.analysis.workflows.nodes.supervisor_config import (
    build_agent_list_variable,
)

# Get prompt manager
prompt_manager = get_prompt_manager()

# Build variables
agent_list = build_agent_list_variable()

# Fetch prompt with fallback
try:
    supervisor_prompt = await prompt_manager.get_prompt(
        name="analysis-supervisor-routing",
        variables={"agent_list": agent_list},
        label="production",
    )

    # Get metadata for trace
    prompt_metadata = await prompt_manager.get_prompt_metadata(
        name="analysis-supervisor-routing",
        label="production",
    )

except Exception as e:
    # Fallback to hardcoded SUPERVISOR_PROMPT constant
    supervisor_prompt = SUPERVISOR_PROMPT
    prompt_metadata = {"prompt_source": "hardcoded_constant"}
```

## Migration Script

Upload all hardcoded prompts to Langfuse:

```bash
# Dry run (preview)
poetry run python scripts/migrate_prompts_to_langfuse.py

# Execute upload
poetry run python scripts/migrate_prompts_to_langfuse.py --execute

# Upload with custom label
poetry run python scripts/migrate_prompts_to_langfuse.py --execute --label staging
```

## Prompt Naming Convention

**Format**: `{domain}-{component}-{variant}`

Examples:
- `analysis-supervisor-routing` - Supervisor routing prompt
- `analysis-agent-tech-comparator` - Tech comparator agent prompt
- `analysis-synthesis-core` - Core synthesis prompt
- `tutor-lesson-delivery` - Tutor lesson delivery prompt

## Hardcoded Prompts

Currently supported hardcoded prompts (fallback):

1. `analysis-supervisor-routing` - Supervisor routing prompt (MIGRATED in Phase 2)

Additional prompts will be added in future phases:
- 8 analysis agent prompts (Phase 3)
- 3 synthesis prompts (Phase 4)
- 8 tutor prompts (Phase 5)

## Cache Behavior

### L1 Cache (In-Memory LRU)
- **TTL**: 5 minutes (configurable via `LANGFUSE_PROMPTS_L1_TTL`)
- **Size**: 100 prompts
- **Scope**: Per-worker (not shared)
- **Eviction**: LRU (least recently used)
- **Use case**: Fast access for hot prompts

### L2 Cache (Redis)
- **TTL**: 15 minutes (configurable via `LANGFUSE_PROMPTS_L2_TTL`)
- **Scope**: Shared across all workers
- **Use case**: Shared cache to reduce Langfuse API calls
- **Disable**: Set `LANGFUSE_PROMPTS_REDIS_ENABLED=false`

### L3 Source (Langfuse API)
- **Latency**: ~100-200ms
- **Use case**: Source of truth for prompt content
- **Fallback**: Uses hardcoded prompts if API unavailable

## Testing

Run tests:

```bash
# Unit tests
poetry run pytest tests/unit/shared/services/prompts/ -v

# Specific test
poetry run pytest tests/unit/shared/services/prompts/test_prompt_manager.py::TestPromptManager::test_l1_cache_hit -v
```

## Observability

The system logs all cache hits/misses and fallbacks:

```python
# L1 cache hit
logger.debug("prompt_cache_l1_hit", name=name, label=label)

# L2 cache miss
logger.debug("prompt_cache_l2_miss", name=name, label=label)

# Langfuse fetch
logger.info(
    "prompt_langfuse_fetched",
    name=name,
    label=label,
    version=prompt_obj.version,
)

# Fallback to hardcoded
logger.info(
    "prompt_fallback_to_hardcoded",
    name=name,
    message="Using hardcoded prompt as fallback",
)
```

## Rollout Plan

### Phase 1: Infrastructure (Complete)
- PromptManager implementation
- Multi-level caching
- Configuration settings
- Unit tests (23 tests, 100% coverage)

### Phase 2: Supervisor Migration (Complete)
- Migrated `analysis-supervisor-routing` prompt
- Added `build_agent_list_variable()` helper
- Supervisor node updated to use PromptManager
- Trace attribution added

### Phase 3: Agent Prompts (Planned)
- Migrate 8 agent prompts in batches
- Monitor cache hit rates and latency

### Phase 4: Synthesis Prompts (Planned)
- Migrate 3 synthesis prompts
- Test complex variable substitution

### Phase 5: Tutor Prompts (Planned)
- Migrate 8 tutor prompts
- Complete migration

## Troubleshooting

### Prompt not found error

```
ValueError: Prompt 'xyz' not found in Langfuse or hardcoded fallbacks
```

**Solution**: Add prompt to `HARDCODED_PROMPTS` dict in `prompt_manager.py`, or upload to Langfuse.

### Redis connection errors

```
redis.exceptions.ConnectionError: Connection closed by server
```

**Solution**: Disable Redis L2 cache temporarily:
```bash
LANGFUSE_PROMPTS_REDIS_ENABLED=false
```

### Langfuse API unavailable

The system automatically falls back to hardcoded prompts. Check logs:

```
prompt_fallback_to_hardcoded: Using hardcoded prompt as fallback
```

No action needed - system continues operating offline.

## Performance Metrics

Expected cache hit rates (after warm-up):
- **L1 Cache**: 90-95% (hot prompts)
- **L2 Cache**: 4-9% (shared across workers)
- **Langfuse API**: <1% (new prompts or cache misses)
- **Fallback**: <0.1% (API failures only)

Expected latency (P95):
- **L1 hit**: <1ms
- **L2 hit**: 5-10ms
- **Langfuse API**: 100-200ms
- **Fallback**: <1ms

## Future Enhancements

1. **A/B Testing**: Built-in support for prompt experiments
2. **Prompt Playground**: Integration with Langfuse UI for testing
3. **Cost Tracking**: Track cost per prompt version
4. **Auto-reload**: Hot reload prompts without restart
5. **Metrics Dashboard**: Cache hit rates, latency, costs

## Related Documentation

- Issue spec: `docs/issues/379-prompt-management/README.md`
- Migration script: `scripts/migrate_prompts_to_langfuse.py`
- Test suite: `tests/unit/shared/services/prompts/`
- Langfuse docs: https://langfuse.com/docs/prompts/get-started
