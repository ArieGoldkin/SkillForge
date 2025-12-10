# Issue #220: PII/Safety Guardrails and Vector Cleanup

**Status:** Planning (December 10, 2025)
**Sprint:** Sprint 8 - Embeddings & Search
**Priority:** MEDIUM
**Estimated Effort:** 3-4 days

---

## Overview

Add optional PII/safety guardrails before embedding, and implement cleanup/integrity routines for vector storage (orphans, corruption). This ensures sensitive content is flagged (not logged) before embedding, and maintains database integrity for the vector store.

---

## Key Design Decisions

### 1. PII Detection: Hybrid Regex + Optional Presidio

**Approach:** Start with fast regex patterns for common PII types, with optional Presidio integration for production environments needing higher accuracy.

| PII Type | Detection Method | Performance |
|----------|------------------|-------------|
| Email | Regex | ~0.1ms |
| Phone (US/Intl) | Regex | ~0.1ms |
| SSN | Regex | ~0.1ms |
| Credit Card | Regex + Luhn | ~0.2ms |
| IP Address | Regex | ~0.1ms |
| API Keys | Regex patterns | ~0.2ms |
| Names/Orgs | Presidio (optional) | ~50ms |

**Decision:** Regex-first for speed, Presidio opt-in for higher sensitivity.

### 2. Integration Point: Pre-Chunking

**Location:** `chunk_content.py` (before `build_chunks()`)

```
extract_content() → raw_content
       ↓
[PII SCREENING] ← Single pass, full document context
       ↓
chunk_document() → ChunkText[]
       ↓
generate_embeddings() → vectors
       ↓
store_embeddings() → database
```

**Why Pre-Chunking:**
- Single pass through entire document
- Full context for better detection
- Cleaner data for all downstream services
- Can reject early if PII density too high
- Works with existing dedup system

### 3. PII Handling: Flag, Don't Log

**Critical Privacy Requirement:** Never log detected PII values.

```python
# ✅ CORRECT: Log type and count only
logger.warning("pii_detected", pii_types=["email", "phone"], count=3)

# ❌ WRONG: Never log actual values
logger.warning("pii_detected", values=["john@email.com", "555-1234"])
```

**Database Storage:**
- `pii_flag: bool` - Whether PII was detected
- `pii_types: list[str]` - Types found (not values)
- No raw PII stored anywhere

### 4. Cleanup Strategy: Scheduled + On-Demand

| Cleanup Type | Trigger | Frequency |
|--------------|---------|-----------|
| Orphan chunks | Scheduled job | Daily |
| Corrupted vectors | Scheduled job | Daily |
| Draft TTL | Scheduled job | Daily |
| Integrity check | On-demand | Before search |

---

## Architecture

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                     PII/SAFETY GUARDRAILS ARCHITECTURE                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────────┐    ║
║  │                        PRE-EMBEDDING LAYER                          │    ║
║  └─────────────────────────────────────────────────────────────────────┘    ║
║                                                                              ║
║     ┌──────────┐    ┌──────────────┐    ┌───────────────┐    ┌─────────┐   ║
║     │   RAW    │───▶│     PII      │───▶│   CHUNKER     │───▶│ EMBEDDER│   ║
║     │ CONTENT  │    │   SCREENER   │    │               │    │         │   ║
║     │          │    │  (optional)  │    │               │    │         │   ║
║     └──────────┘    └──────────────┘    └───────────────┘    └─────────┘   ║
║                            │                                                 ║
║                            ▼                                                 ║
║                     ┌──────────┐                                            ║
║                     │  FLAGS   │ pii_flag, pii_types                        ║
║                     │ (no raw) │ stored in chunk metadata                   ║
║                     └──────────┘                                            ║
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────────┐    ║
║  │                       CLEANUP & INTEGRITY                           │    ║
║  └─────────────────────────────────────────────────────────────────────┘    ║
║                                                                              ║
║     ┌──────────┐    ┌──────────────┐    ┌───────────────┐                   ║
║     │  ORPHAN  │    │   VECTOR     │    │   DRAFT TTL   │                   ║
║     │  CLEANUP │    │  INTEGRITY   │    │    CLEANUP    │                   ║
║     │          │    │    CHECK     │    │               │                   ║
║     └──────────┘    └──────────────┘    └───────────────┘                   ║
║          │                │                    │                             ║
║          └────────────────┴────────────────────┘                             ║
║                          │                                                   ║
║                          ▼                                                   ║
║                   ┌──────────────┐                                          ║
║                   │   CLEANUP    │  Scheduled daily or on-demand            ║
║                   │   SERVICE    │  Hard delete (FK cascade)                ║
║                   └──────────────┘                                          ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## File Structure

```
backend/app/
├── services/
│   ├── pii/
│   │   ├── __init__.py
│   │   ├── detector.py          # PIIDetector class with regex patterns
│   │   ├── patterns.py          # PII regex patterns (email, phone, SSN, etc.)
│   │   └── types.py             # PIIResult, PIIType enums
│   ├── cleanup/
│   │   ├── __init__.py
│   │   ├── orphan_cleaner.py    # Orphan chunk detection and removal
│   │   ├── integrity_checker.py # Vector integrity validation
│   │   └── ttl_manager.py       # Draft expiration cleanup
│   └── validation/
│       └── vector_validator.py  # EXISTING - extend for integrity checks
├── workflows/tasks/
│   └── chunk_content.py         # MODIFY - add PII screening hook
├── models/
│   └── analysis_chunk.py        # MODIFY - add pii_flag, pii_types columns
└── core/
    └── config.py                # MODIFY - add PII/cleanup config settings
```

---

## Configuration (Environment Variables)

### PII Screening
```bash
# Enable/disable PII screening (default: false for dev, true for prod)
PII_SCREENING_ENABLED=true

# Sensitivity level: low (emails only), medium (+ phone, SSN), high (+ names via NER)
PII_SENSITIVITY_LEVEL=medium

# Action on PII detection: flag (add metadata), reject (fail workflow)
PII_ACTION=flag

# Reject if PII density exceeds threshold (% of chunks with PII)
PII_REJECT_THRESHOLD=0.3

# Enable Presidio for NER-based detection (requires presidio-analyzer)
PII_USE_PRESIDIO=false
```

### Cleanup & Integrity
```bash
# Enable scheduled cleanup jobs
CLEANUP_ENABLED=true

# Draft TTL in days (analyses with status='draft' older than this are deleted)
CLEANUP_DRAFT_TTL_DAYS=7

# Batch size for cleanup operations
CLEANUP_BATCH_SIZE=1000

# Enable vector integrity checks
VECTOR_INTEGRITY_CHECK_ENABLED=true
```

---

## Implementation Phases

### Phase 1: PII Detection Service (Day 1)

**Goal:** Create configurable PII detector with regex patterns

**Deliverables:**
1. `services/pii/patterns.py` - Regex patterns for common PII
2. `services/pii/types.py` - PIIType enum, PIIResult dataclass
3. `services/pii/detector.py` - PIIDetector class
4. `tests/unit/services/pii/test_detector.py` - Unit tests

**PII Types Detected:**
- Email addresses
- Phone numbers (US, international)
- Social Security Numbers (SSN)
- Credit card numbers (with Luhn validation)
- IP addresses (v4, v6)
- API keys (AWS, GitHub, Stripe patterns)

### Phase 2: Pipeline Integration (Day 1-2)

**Goal:** Integrate PII screening into embedding pipeline

**Deliverables:**
1. Modify `chunk_content.py` - Add screening before chunking
2. Modify `analysis_chunk.py` - Add `pii_flag`, `pii_types` columns
3. Migration script for new columns
4. Config settings in `config.py`
5. Integration tests

**Integration Flow:**
```python
async def chunk_content(state: AnalysisState) -> dict:
    text = state["raw_content"]

    # NEW: PII screening
    if settings.PII_SCREENING_ENABLED:
        pii_result = pii_detector.scan(text)
        if pii_result.should_reject:
            raise PIIRejectError(pii_types=pii_result.types)
        # Store flags in state for downstream storage
        state["pii_flags"] = pii_result.to_metadata()

    # Existing chunking logic...
```

### Phase 3: Cleanup Services (Day 2-3)

**Goal:** Implement orphan cleanup, integrity checks, draft TTL

**Deliverables:**
1. `services/cleanup/orphan_cleaner.py` - Detect and remove orphan chunks
2. `services/cleanup/integrity_checker.py` - Validate vector dimensions/values
3. `services/cleanup/ttl_manager.py` - Expire old drafts
4. CLI commands or API endpoints for manual cleanup
5. Unit tests for each service

**Cleanup SQL Queries:**
```sql
-- Orphan detection (chunks without valid analysis)
SELECT c.id FROM analysis_chunks c
LEFT JOIN analyses a ON c.analysis_id = a.id
WHERE a.id IS NULL;

-- Vector integrity (dimension mismatch)
SELECT id FROM analysis_chunks
WHERE vector IS NOT NULL
AND array_length(vector::float[], 1) != 1536;

-- Draft TTL (old drafts)
SELECT id FROM analyses
WHERE status = 'draft'
AND created_at < NOW() - INTERVAL '7 days';
```

### Phase 4: Documentation & Testing (Day 3-4)

**Goal:** Complete documentation and comprehensive testing

**Deliverables:**
1. Update this README with final implementation details
2. Create `ARCHITECTURE_DESIGN.md` with technical deep-dive
3. Add compliance notes (GDPR, SOC2 considerations)
4. Load testing for PII screening performance
5. Integration tests with real-world content

---

## Database Schema Changes

### Migration: Add PII Columns to analysis_chunks

```python
# alembic/versions/YYYYMMDD_add_pii_columns.py

def upgrade():
    op.add_column('analysis_chunks',
        sa.Column('pii_flag', sa.Boolean(), nullable=True, default=False))
    op.add_column('analysis_chunks',
        sa.Column('pii_types', JSONB(), nullable=True))

    # Index for PII queries
    op.create_index('ix_analysis_chunks_pii_flag',
        'analysis_chunks', ['pii_flag'],
        postgresql_where=text('pii_flag = true'))

def downgrade():
    op.drop_index('ix_analysis_chunks_pii_flag')
    op.drop_column('analysis_chunks', 'pii_types')
    op.drop_column('analysis_chunks', 'pii_flag')
```

---

## PII Detection Patterns

### Regex Patterns (patterns.py)

```python
PII_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",

    "phone_us": r"\b(?:\+1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",

    "ssn": r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",

    "credit_card": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b",

    "ipv4": r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",

    "aws_key": r"\b(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b",

    "github_token": r"\b(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36}\b",
}
```

---

## Performance Requirements

| Operation | Target Latency | Notes |
|-----------|---------------|-------|
| Regex PII scan (1KB) | < 1ms | Compiled patterns |
| Regex PII scan (100KB) | < 50ms | Full document |
| Presidio scan (1KB) | < 100ms | NER-based |
| Orphan cleanup (1000 rows) | < 5s | Batch delete |
| Integrity check (1000 rows) | < 2s | Batch query |

---

## Success Criteria

- [ ] PII screening can be enabled/disabled via config
- [ ] When enabled, flagged rows recorded without logging raw sensitive text
- [ ] Support for email, phone, SSN, credit card, IP, API keys
- [ ] Orphan cleanup removes stray vectors (coarse/fine) without harming active analyses
- [ ] Integrity check detects and reports bad vectors (dimension mismatch, NaN, zero)
- [ ] Draft TTL cleanup expires old draft analyses
- [ ] Queries remain robust (skip corrupted vectors gracefully)
- [ ] Docs updated with usage and compliance notes
- [ ] Unit tests cover 80%+ of new code
- [ ] Integration tests verify pipeline behavior

---

## Related Issues

- **#215:** Embedding Pipeline Hardening - Foundation (chunk hashing, batch embedding)
- **#216:** Retrieval & Search API - Benefits from clean vectors
- **#217:** Re-Ranker - Uses chunk metadata
- **#218:** Telemetry & Backpressure - Shares vector validation patterns
- **#221:** Hierarchical Chunking - PII flags propagate through granularity levels

---

## Compliance Notes

### GDPR Considerations
- PII detection helps identify personal data before embedding
- Flagging allows for data subject access requests (find all chunks with PII)
- No actual PII values stored in logs or metadata

### SOC2 Considerations
- Configurable sensitivity levels support different compliance requirements
- Audit trail via structured logging (detection events, not values)
- Cleanup routines support data retention policies

---

## Next Steps

1. **Review this plan** - Confirm approach and scope
2. **Create feature branch** - `feature/220-pii-safety-guardrails` ✅
3. **Phase 1 implementation** - PII detection service
4. **Phase 2 implementation** - Pipeline integration
5. **Phase 3 implementation** - Cleanup services
6. **Phase 4 completion** - Documentation and testing
7. **PR to dev** - With full test suite passing

---

**Last Updated:** December 10, 2025
**Author:** Claude Code with AI/ML Engineer, Backend Architect, Security Checklist Skill
**Status:** Planning → Ready for Review
