# Retrieval Failure Quick Reference

Quick lookup guide for the 18 failed retrieval evaluation queries.

## At a Glance

- **Pass Rate**: 91.1% (185/203)
- **Target**: 95% (need to fix 8 queries)
- **Main Issue**: Ranking problem (expected chunks exist but rank too low)
- **Quick Win**: Section title boosting (+4 queries, 1-2 days effort)

## Failed Queries by Category

### Trivial (1 failure)
- `q-llm-agents-intro` - agents tool use reasoning

### Easy (8 failures)
- `q-tot-applications` - Tree-of-Thoughts use cases (RANK 8)
- `q-langgraph-supervisor` - supervisor pattern (RANK 6)
- `q-langsmith-metrics` - custom evaluators (NOT IN TOP-10)
- `q-mlops-best-practices` - MLOps CI/CD (NOT IN TOP-10)
- `q-uber-matching` - driver-rider matching
- `q-uber-surge` - surge pricing
- `q-perplexity-retrieval` - Perplexity RAG
- `q-terraform-iac` - Terraform IaC

### Medium (7 failures)
- `q-langgraph-production` - production deployment (NOT IN TOP-10)
- `q-rag-groundedness` - hallucination prevention
- `q-rag-answer-relevance` - answer relevance metric
- `q-uber-ringpop` - consistent hashing
- `q-uber-geospatial` - H3 hexagonal grid
- `q-sem-paraphrase-retrieval` - paraphrase test
- `q-sem-concept-matching` - concept matching test

### Hard (1 failure)
- `q-cross-agent-memory-rag` - multi-document synthesis

### Adversarial (1 failure)
- `q-edge-very-long` - 249-word compound query (EXPECTED FAILURE)

## Root Cause Taxonomy

```
Ranking Issue (Top-5 Miss) .......... 50% (9 queries)
├─ Expected chunk in positions 6-10
└─ FIX: Section title boosting

Missing from Top-10 ................. 22% (4 queries)  
├─ Similar content in wrong document
└─ FIX: Document-aware scoring

Technical Jargon .................... 17% (3 queries)
├─ Uber-specific terminology
└─ FIX: Query expansion

Cross-Document Synthesis ............ 6%  (1 query)
├─ Expects multiple documents
└─ FIX: MMR reranking

Adversarial Edge Case ............... 6%  (1 query)
└─ FIX: None (acceptable)
```

## Priority Fixes

### 1. Section Title Boosting (Priority 1)
**Impact**: +4 queries → 94% pass rate  
**Effort**: LOW (1-2 days)

Boost chunks by 1.5x when query terms appear in `section_title`:
```python
# Pseudo-code
if any(query_term in chunk.section_title for query_term in query_terms):
    chunk.score *= 1.5
```

**Fixes**:
- q-tot-applications (applications in title)
- q-langgraph-supervisor (patterns in title)
- q-uber-matching (matching-algorithm in title)
- q-uber-surge (surge-pricing in title)

### 2. Hybrid Weight Tuning (Priority 2)
**Impact**: +6 queries → 96% pass rate  
**Effort**: MEDIUM (3-5 days)

Boost keyword search for technical queries:
```python
# Pseudo-code
technical_terms = ["LangGraph", "LangSmith", "Terraform", "MLOps", ...]
if count_technical_terms(query) >= 3:
    keyword_weight *= 1.2
```

**Fixes**:
- q-langsmith-metrics (LangSmith, custom, evaluators, metrics)
- q-mlops-best-practices (MLOps, CI/CD, automation, practices)
- q-terraform-iac (Terraform, infrastructure, code, declarative)
- q-langgraph-production (LangGraph, production, deployment, checkpointing)
- Plus 2 more from ranking issues

### 3. Document-Aware Scoring (Priority 3)
**Impact**: +3 queries → 97% pass rate  
**Effort**: MEDIUM (3-5 days)

Use document path to disambiguate:
```python
# Pseudo-code
if query contains "multiagent":
    boost chunks with path like "*/multiagent/*"
elif query contains "framework":
    boost chunks with path like "*/framework/*"
```

**Fixes**:
- q-langgraph-production (multiagent vs framework)
- q-langsmith-metrics (evaluation vs observability)
- Plus 1 more

## Validation Commands

```bash
# Run full evaluation (203 queries)
poetry run python scripts/evaluation/run_evaluation.py \
  --expanded --output /tmp/eval_current.json

# Check specific failed queries
poetry run python -c "
import json
with open('/tmp/eval_current.json') as f:
    data = json.load(f)
    for diff in ['trivial', 'easy', 'medium', 'hard', 'adversarial']:
        failed = data['results'][diff]['failed_example_ids']
        if failed:
            print(f'{diff}: {failed}')
"

# Quick pass rate check
jq '.total_passed, .total_examples, (.total_passed/.total_examples*100)' /tmp/eval_current.json
```

## Files

- `docs/retrieval-evaluation-failure-analysis.md` - Full analysis (7KB)
- `docs/retrieval-failure-classification.json` - JSON data (4KB)
- `docs/RETRIEVAL_FAILURE_QUICKREF.md` - This file

## Next Steps

1. Implement section title boosting (1-2 days)
2. Re-run evaluation, expect 189/203 pass (93%)
3. Implement hybrid weight tuning (3-5 days)
4. Re-run evaluation, expect 194/203 pass (96%)
5. Close issue when pass rate > 95%

---
Last updated: 2025-12-18
