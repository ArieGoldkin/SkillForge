# Issue #255: Difficulty Stratification

**Sprint**: 12 (Evaluation Dataset)
**Points**: 3
**Priority**: MUST HAVE
**Status**: ✅ COMPLETE

## Objective

Label all evaluation queries with difficulty levels (trivial/easy/medium/hard/adversarial) and document clear criteria for each level.

## Current State Analysis

```
CURRENT DIFFICULTY COVERAGE
============================

Dataset                          | Difficulty Field | Current Values
---------------------------------|------------------|----------------
agent_analysis_golden_v2.json    | YES              | medium (2), hard (1)
edge_cases_v2.json               | YES              | hard (~35), adversarial (5)
queries.json (retrieval fixtures)| NO               | N/A (no difficulty field)

SCHEMA STATUS
=============
- Current schema: ["easy", "medium", "hard", "expert", "adversarial"]
- Sprint spec: ["trivial", "easy", "medium", "hard", "adversarial"]
- ACTION: Update schema to add "trivial" (replace "expert")
```

## Difficulty Criteria

| Level | Criteria | Expected Similarity | Example |
|-------|----------|---------------------|---------|
| **Trivial** | Exact keyword match | >0.85 | "JWT", "OAuth2 password flow" |
| **Easy** | Common synonyms | >0.70 | "secure web API methods" |
| **Medium** | Paraphrased intent | >0.55 | "making queries faster" |
| **Hard** | Multi-hop reasoning | >0.40 | "compare React hooks to Vue composition" |
| **Adversarial** | Edge cases/robustness | Graceful degradation | Injection, misspellings, off-domain |

## Implementation Plan

### Phase 1: Schema & Documentation
1. Update `dataset_v2_schema.json` - add "trivial" to difficulty enum
2. Create difficulty criteria section in `FIXTURE_GUIDE.md`
3. Create issue #255 documentation

### Phase 2: Label Queries
4. Add difficulty field to all 21 queries in `queries.json`
5. Verify distribution: min 3 per difficulty level
6. Update v2 datasets if needed

### Phase 3: Validation & Testing
7. Add difficulty validation to `validation.py`
8. Add unit tests for difficulty validation
9. Run CI checks and verify

## Proposed Query Labels (queries.json)

| Query ID | Category | Difficulty | Rationale |
|----------|----------|------------|-----------|
| q-oauth2-impl | specific | trivial | Exact term match |
| q-jwt-expiry | specific | easy | Synonym: "best practices" |
| q-async-await | specific | trivial | Direct keyword match |
| q-react-state | specific | easy | Slight paraphrase |
| q-sql-join | specific | trivial | Direct SQL terms |
| q-langchain-tools | specific | easy | Specific but conceptual |
| q-api-security-broad | broad | medium | Multi-section expected |
| q-deployment-broad | broad | medium | Cross-domain query |
| q-neg-quantum | negative | adversarial | Off-domain test |
| q-neg-rust | negative | adversarial | Wrong language test |
| q-sem-synonym | specific | easy | Synonym test |
| q-sem-paraphrase | specific | medium | Paraphrase test |
| q-k8s-scaling | specific | easy | Technical terms |
| q-vector-search | specific | medium | Conceptual understanding |
| q-edge-short | edge | adversarial | Single term test |
| q-edge-special | edge | adversarial | Special chars test |
| q-c2f-tools-coarse | coarse-to-fine | medium | Hierarchy test |
| q-c2f-tools-fine | coarse-to-fine | hard | Specific paragraph |
| q-c2f-react-coarse | coarse-to-fine | medium | Architecture query |
| q-c2f-react-fine | coarse-to-fine | hard | Specific pattern |
| q-c2f-intro-hierarchy | coarse-to-fine | hard | Multi-level match |

**Distribution**: Trivial: 3, Easy: 5, Medium: 6, Hard: 3, Adversarial: 4 = 21 total

## Files to Modify

| File | Changes |
|------|---------|
| `app/evaluation/schemas/dataset_v2_schema.json` | Add "trivial" to difficulty enum |
| `tests/smoke/retrieval/fixtures/queries.json` | Add difficulty field to 21 queries |
| `docs/issues/223-retrieval-smoke-tests/FIXTURE_GUIDE.md` | Add difficulty criteria section |
| `app/evaluation/schemas/validation.py` | Add difficulty validation |
| `tests/unit/evaluation/test_validation.py` | Add difficulty validation tests |

## Files to Create

| File | Purpose |
|------|---------|
| `docs/issues/255-difficulty-stratification/README.md` | Issue documentation |

## Acceptance Criteria

- [x] Schema updated with "trivial" difficulty level
- [x] All 21 queries labeled with difficulty
- [x] At least 3 queries per difficulty level
- [x] Difficulty criteria documented in FIXTURE_GUIDE.md
- [x] Validation function checks difficulty field
- [x] Unit tests for difficulty validation
- [x] All CI checks passing

## Verification

```
✅ All 26 validation tests passing
✅ ruff format --check app/ tests/ - PASS
✅ ruff check app/ - PASS
✅ mypy app/evaluation/schemas/validation.py - PASS
✅ Query fixture validation: is_valid=True, example_count=21
✅ Distribution: trivial: 3, easy: 5, medium: 6, hard: 3, adversarial: 4
```

## Dependencies

- #252 Schema v2.0 (COMPLETE)
- #254 Edge Cases (COMPLETE - already uses hard/adversarial)
