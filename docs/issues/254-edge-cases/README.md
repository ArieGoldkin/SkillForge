# Issue #254: Edge Case Examples Generation

**Sprint**: 12 (Evaluation Dataset)
**Points**: 5
**Priority**: MUST HAVE
**Status**: ✅ COMPLETE
**Commit**: `31c2b9c`

## Objective

Generate 40+ edge case examples to test agent robustness against unusual inputs, covering 8 distinct failure mode categories.

## Edge Case Categories

| Category | Count | Description | Difficulty |
|----------|-------|-------------|------------|
| **Very Short** | 5 | 1-2 word queries ("React?", "help") | hard |
| **Very Long** | 5 | 10K+ word articles | hard |
| **Special Characters** | 5 | Unicode, emojis, malformed code blocks | hard |
| **Misspellings** | 5 | Common typos ("Reavt", "Pytohn") | hard |
| **Ambiguous** | 5 | Routes to 3+ agents | hard |
| **Minimal Context** | 5 | Missing key information | hard |
| **Contradictory** | 5 | Self-contradicting claims | adversarial |
| **Multilingual** | 5 | Non-English or mixed language | hard |

## Deliverables

### 1. Edge Case Templates (`app/evaluation/ingestion/edge_case_templates.py`)

Template content and patterns for generating edge cases:

```python
from app.evaluation.ingestion.edge_case_templates import EdgeCaseTemplates

templates = EdgeCaseTemplates()

# Get very short queries
queries = templates.get_very_short_queries()
# ["React?", "help", "Python", "fast?", "best", ...]

# Generate long content
long_content = templates.generate_long_content(word_count=10000)

# Apply misspellings
typo_text = templates.apply_misspellings("React and Python", typo_rate=0.3)
# "Reavt and Pytohn"

# Get multilingual content
spanish = templates.get_multilingual_content("spanish")
# "¿Cómo implementar autenticación JWT en FastAPI?"
```

### 2. Edge Case Generator (`app/evaluation/ingestion/edge_case_generator.py`)

Main generator class with methods for each category:

```python
from app.evaluation.ingestion import EdgeCaseGenerator

generator = EdgeCaseGenerator()

# Generate all 40 edge cases (8 categories × 5 each)
examples = generator.generate_all(examples_per_category=5)

# Generate specific category
short_examples = generator.generate_category("very_short", count=5)

# Save as v2.0 dataset
generator.save_dataset(examples, "datasets/edge_cases_v2.json")
```

### 3. CLI Script (`scripts/generate_edge_cases.py`)

Command-line interface for generation:

```bash
# Generate all 40 edge cases
python scripts/generate_edge_cases.py --output datasets/edge_cases_v2.json

# Generate specific category
python scripts/generate_edge_cases.py --category misspellings --count 10

# Validate against v2.0 schema
python scripts/generate_edge_cases.py --validate
```

## Expected Behaviors

Each category defines graceful degradation behaviors:

| Category | Expected Response | Forbidden Behaviors |
|----------|-------------------|---------------------|
| Very Short | Request clarification or generic help | Crash, hang, hallucinate |
| Very Long | Proper chunking, summary if needed | Memory error, silent truncation |
| Special Characters | Normalize or strip problematic chars | Encoding errors, garbled output |
| Misspellings | Fuzzy match to correct technology | Misroute, fail recognition |
| Ambiguous | Route to multiple agents or clarify | Single incorrect agent |
| Minimal Context | Request missing info or generic response | Hallucinate missing details |
| Contradictory | Identify conflict, flag as conflicting | Assert one side without noting |
| Multilingual | Attempt processing or respond in language | Crash on non-ASCII |

## v2.0 Schema Compliance

Each edge case example follows this structure:

```json
{
  "id": "edge-{category}-{number}",
  "inputs": {
    "content": "...",
    "content_type": "article|query|code"
  },
  "expected_outputs": {
    "primary": {
      "behavior": "graceful_degradation|error_message|fallback",
      "expected_error": "optional error message"
    },
    "acceptable_alternatives": [],
    "forbidden_outputs": [
      {"note": "Should NOT crash or hang"},
      {"note": "Should NOT produce hallucinated content"}
    ]
  },
  "evaluation_criteria": {
    "scoring_rubric": {
      "correctness": {"weight": 0.4},
      "completeness": {"weight": 0.3},
      "quality": {"weight": 0.3}
    }
  },
  "provenance": {
    "source": "synthetic",
    "created_at": "2025-12-10T00:00:00Z",
    "created_by": "edge_case_generator"
  },
  "validation": {
    "status": "draft"
  },
  "metadata": {
    "difficulty": "hard|adversarial",
    "edge_case": true,
    "adversarial": false,
    "tags": ["edge-case", "{category}", "robustness"],
    "edge_case_category": "{category}"
  }
}
```

## Example Edge Cases by Category

### Very Short (edge-short-001 to edge-short-005)
| ID | Content | Expected Behavior |
|----|---------|-------------------|
| edge-short-001 | `"React?"` | Graceful error: "Query too short. Please provide more context." |
| edge-short-002 | `"help"` | Fallback to generic help response |
| edge-short-003 | `"Python vs"` | Error: "Incomplete comparison" |
| edge-short-004 | `"fast?"` | Error: "Ambiguous query" |
| edge-short-005 | `"API"` | Graceful degradation to general API info |

### Misspellings (edge-typo-001 to edge-typo-005)
| ID | Content | Expected Behavior |
|----|---------|-------------------|
| edge-typo-001 | `"Reavt vs Veu comparison"` | Fuzzy match to "React vs Vue" |
| edge-typo-002 | `"Pytohn FastAPi tutorial"` | Correct recognition |
| edge-typo-003 | `"TypeScipt authentication"` | Route to correct agent |
| edge-typo-004 | `"Postgress database setup"` | Recognize PostgreSQL |
| edge-typo-005 | `"Kuberneets deployment"` | Recognize Kubernetes |

### Ambiguous (edge-ambig-001 to edge-ambig-005)
| ID | Potential Agents | Content |
|----|------------------|---------|
| edge-ambig-001 | tech_comparator, security_auditor, implementation_planner | "Is React secure for building authenticated APIs? How to set up?" |
| edge-ambig-002 | 4+ agents | "Modern React app with auth, performance optimization, and CI/CD" |
| edge-ambig-003 | tech_comparator, trend_validator | "Is Vue still relevant compared to React in 2025?" |

### Multilingual (edge-multi-001 to edge-multi-005)
| ID | Language | Content |
|----|----------|---------|
| edge-multi-001 | Spanish | "¿Cómo implementar autenticación JWT en FastAPI?" |
| edge-multi-002 | French | "Comment optimiser les performances de React en 2025?" |
| edge-multi-003 | German | "Wie integriere ich PostgreSQL mit FastAPI?" |
| edge-multi-004 | Code-switching | "Build a `// crear una app` React application" |
| edge-multi-005 | Japanese | "Reactのパフォーマンスを最適化する方法" |

## Files to Create

| File | Lines (est.) | Purpose |
|------|--------------|---------|
| `app/evaluation/ingestion/edge_case_templates.py` | ~150 | Template content and patterns |
| `app/evaluation/ingestion/edge_case_generator.py` | ~300 | Main generator class |
| `scripts/generate_edge_cases.py` | ~80 | CLI script |
| `tests/unit/evaluation/test_edge_case_generator.py` | ~250 | Unit tests |
| `app/evaluation/datasets/edge_cases_v2.json` | ~1500 | Generated 40 examples |

## Files to Modify

| File | Changes |
|------|---------|
| `app/evaluation/ingestion/__init__.py` | Add EdgeCaseGenerator exports |

## Test Coverage

| Test Class | Tests | Description |
|------------|-------|-------------|
| TestEdgeCaseTemplates | 6 | Template content generation |
| TestEdgeCaseGenerator | 15 | Generator methods |
| TestEdgeCaseCategories | 8 | One per category validation |
| TestSchemaCompliance | 5 | v2.0 schema validation |
| **Total** | **~34** | Target 80%+ coverage |

## Verification Checklist

- [x] 40 edge cases generated (8 categories × 5 each)
- [x] All examples pass v2.0 schema validation
- [x] All examples have `edge_case: true` in metadata
- [x] Difficulty is "hard" or "adversarial" for all examples
- [x] Expected behaviors documented for each category
- [x] All 61 unit tests passing
- [x] All lint checks passing (ruff format, ruff check, mypy)
- [x] CLI script functional with --validate option

## Dependencies

- #252 Schema v2.0 (completed)
- Existing `validation.py` for schema validation
- Existing `agent_config.py` for valid agent types

## Implementation Phases

### Phase 1: Foundation
1. Create `edge_case_templates.py` with template content
2. Create `edge_case_generator.py` with base class structure
3. Implement `_build_example()` method for v2.0 compliance

### Phase 2: Category Generators
4. Implement `_generate_very_short()` and `_generate_very_long()`
5. Implement `_generate_special_characters()` and `_generate_misspellings()`
6. Implement `_generate_ambiguous()` and `_generate_minimal_context()`
7. Implement `_generate_contradictory()` and `_generate_multilingual()`

### Phase 3: CLI and Validation
8. Create `generate_edge_cases.py` CLI script
9. Implement `generate_all()` orchestration method
10. Add schema validation to CLI

### Phase 4: Testing and Generation
11. Write unit tests for all generator methods
12. Generate final 40 examples to `edge_cases_v2.json`
13. Validate all examples pass schema validation
14. Update `__init__.py` with exports

## Commits

1. `31c2b9c` - feat(#254): add edge case generator with 40 examples across 8 categories

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `app/evaluation/ingestion/edge_case_templates.py` | 401 | Template content for all 8 categories |
| `app/evaluation/ingestion/edge_case_generator.py` | 584 | Main generator class |
| `scripts/generate_edge_cases.py` | 183 | CLI script |
| `tests/unit/evaluation/test_edge_case_generator.py` | 663 | 61 unit tests |
| `app/evaluation/datasets/edge_cases_v2.json` | 2,928 | Generated 40 edge cases |

## Files Modified

| File | Changes |
|------|---------|
| `app/evaluation/ingestion/__init__.py` | Added EdgeCaseGenerator exports |
| `app/evaluation/schemas/dataset_v2_schema.json` | Extended schema for edge cases |
