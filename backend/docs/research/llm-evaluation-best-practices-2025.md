# LLM Evaluation Best Practices (December 2025)

**Research Date:** December 17, 2025
**Purpose:** Improve SkillForge's G-Eval implementation with latest advances
**Current Implementation:** `/backend/app/shared/services/g_eval/scorer.py`

---

## Executive Summary

Based on research of recent papers, production systems (OpenAI Evals, Langfuse, DeepEval, DSPy), and practitioner blogs (Eugene Yan, Anthropic), here are the key findings for improving our G-Eval implementation:

**Key Gaps in Current Implementation:**
1. No self-consistency / multi-sampling
2. No position bias mitigation
3. Limited semantic similarity (heuristic-only fallback)
4. No constrained decoding for structured scores
5. Single-model dependency (no ensemble)

**Quick Wins (High Impact, Low Effort):**
- Add self-consistency voting (3-5 samples per criterion)
- Implement position swapping to reduce bias
- Use structured outputs for score parsing
- Add cost optimization with caching and batching

**Long-Term Improvements:**
- Multi-model ensemble evaluation
- Semantic similarity with modern embeddings
- Automated prompt optimization (DSPy-style)

---

## 1. Latest LLM-as-Judge Advances

### 1.1 Beyond G-Eval: Current State (2024-2025)

**G-Eval (2023) Baseline:**
- Chain-of-thought prompting with 1-5 scoring
- Spearman correlation 0.514 with humans
- Known bias toward LLM-generated text

**Current Best Practices:**

#### OpenAI Evals (2024-2025)
- **Template-based evaluation** (YAML configuration, no custom code)
- **Model-graded evals** as primary method
- **Dashboard integration** for non-technical stakeholders
- **Git-LFS for datasets** (selective fetching)

**Key Insight:** Industry moving toward declarative evaluation configs rather than procedural code.

#### Anthropic Research (2025)
- **Constitutional Classifiers** for safety evaluation (withstood 3,000+ hours red teaming)
- **Statistical approach to model evaluations** for reproducibility
- **Alignment faking detection** revealing complex model behaviors
- **Introspection techniques** examining internal states before generation

**Key Insight:** Focus on reproducibility, statistical rigor, and understanding model internals.

#### DeepEval Framework (2024)
- **G-Eval + custom criteria** with human-like accuracy
- **Local execution** (NLP models + statistical methods) to reduce API costs
- **RAG-specific metrics** (Answer Relevancy, Faithfulness, Contextual Recall/Precision)
- **Agentic metrics** (Task Completion, Tool Correctness, Conversation Completeness)

**Key Insight:** Hybrid approach (local + LLM) saves costs while maintaining quality.

---

## 2. Self-Consistency and Multi-Sampling

### 2.1 Self-Consistency Technique (Wang et al., 2022)

**Core Concept:**
Instead of single greedy decoding, generate multiple reasoning paths and use majority voting.

**Implementation:**
```python
# Instead of:
response = await model.ainvoke(messages)
score = parse_score(response)

# Do this:
responses = await asyncio.gather(*[
    model.ainvoke(messages, temperature=0.7)
    for _ in range(5)  # 5 samples
])
scores = [parse_score(r) for r in responses]
final_score = statistics.mode(scores)  # Majority vote
confidence = scores.count(final_score) / len(scores)  # Agreement ratio
```

**When to Use:**
- Arithmetic/logical reasoning
- Complex evaluation criteria
- High-stakes decisions requiring reliability

**Trade-offs:**
- 5x LLM calls = 5x cost
- Improved accuracy (demonstrated in original paper)
- Higher confidence estimates

### 2.2 Temperature and Sampling Strategy

**Best Practice (Eugene Yan):**
- Temperature 0.7-0.8 for diversity
- Position swapping to avoid bias
- Avoid self-evaluation (model evaluating its own outputs)

**Position Bias Mitigation:**
```python
# Swap order of candidates being compared
prompt_a = f"Compare A vs B: {criterion}"
prompt_b = f"Compare B vs A: {criterion}"
score_ab = await evaluate(prompt_a)
score_ba = await evaluate(prompt_b)
# Average or detect inconsistency
```

---

## 3. Semantic Similarity Metrics

### 3.1 Beyond BERTScore

**Current Options (December 2025):**

| Method | Use Case | Pros | Cons |
|--------|----------|------|------|
| **BERTScore** | General similarity | Established, reproducible | Outdated embeddings (BERT 2018) |
| **MoverScore** | Structured text | Alignment-aware | Computationally expensive |
| **Embedding Cosine** | Fast similarity | Simple, interpretable | Depends on embedding model |
| **MTEB Leaderboard** | Model selection | Benchmarked models | Need to check current leaders |

**Recommended Embedding Models (2024-2025):**
- Check MTEB leaderboard for latest: https://huggingface.co/spaces/mteb/leaderboard
- Look for models optimized for semantic textual similarity (STS) tasks
- Consider multilingual if needed

**Implementation:**
```python
from sentence_transformers import SentenceTransformer, util

# Use modern embedding model (check MTEB leaderboard for latest)
model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')

# Compute embeddings
emb1 = model.encode(output_text, convert_to_tensor=True)
emb2 = model.encode(golden_text, convert_to_tensor=True)

# Cosine similarity
similarity = util.cos_sim(emb1, emb2).item()
```

**Trade-offs:**
- One-time model download (~400MB for all-mpnet-base-v2)
- CPU inference: ~10-50ms per encode
- No API costs

### 3.2 Hybrid Retrieval Pattern (Eugene Yan)

For RAG evaluation, combine:
- **Keyword search (BM25)** for names, acronyms, IDs
- **Semantic embeddings** for synonyms, concepts
- **Metadata filters** for dates, categories

---

## 4. Constrained Decoding and Structured Outputs

### 4.1 The Problem

**Current Regex Parsing:**
```python
score_match = re.search(r"<score>\s*(\d)\s*</score>", response)
score = int(score_match.group(1)) if score_match else 3  # FALLBACK!
```

**Issues:**
- LLM might not follow format
- Silent failures (default to 3)
- Parsing fragility

### 4.2 Structured Output Solution

**OpenAI Structured Outputs (2024):**
```python
from pydantic import BaseModel

class EvaluationScore(BaseModel):
    reasoning: str
    score: int  # 1-5
    confidence: float  # 0.0-1.0

# Force schema compliance
response = await model.with_structured_output(EvaluationScore).ainvoke(messages)
# response.score is guaranteed to be int, no parsing needed
```

**Anthropic (Claude) Approach:**
```python
# Use tool calling for structured output
tools = [{
    "name": "submit_evaluation",
    "description": "Submit evaluation score",
    "input_schema": {
        "type": "object",
        "properties": {
            "reasoning": {"type": "string"},
            "score": {"type": "integer", "minimum": 1, "maximum": 5},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0}
        },
        "required": ["reasoning", "score", "confidence"]
    }
}]
response = await model.ainvoke(messages, tools=tools)
```

**Microsoft Guidance (Eugene Yan Recommendation):**
- "Guidance enforces the schema by injecting tokens that make up the structure"
- Deterministic control over output format
- Eliminates prompt-based format requests

**Benefits:**
- No regex parsing needed
- Guaranteed valid scores
- Better error messages
- Type safety

---

## 5. Cost-Effective Evaluation Strategies

### 5.1 Three-Tier Approach

**Tier 1: Heuristic Filtering (Current Implementation)**
- Fast, synchronous, zero API cost
- Schema validation, structural checks
- Filters obvious failures

**Tier 2: Embedding Similarity (Recommended Addition)**
- Fast local inference (~10-50ms)
- Semantic similarity to golden examples
- No API cost after model download

**Tier 3: LLM-as-Judge (Current G-Eval)**
- Deep evaluation, high cost
- Use only for borderline cases or spot checks
- Cache results aggressively

### 5.2 Sampling Strategy

**Full Evaluation (Expensive):**
- All outputs scored by G-Eval
- 4 criteria × 5 samples = 20 LLM calls per output

**Smart Sampling (Cost-Effective):**
```python
# Tier 1: Heuristic filter (free)
heuristic_score = score_output_quality(output, golden, agent_type)

if heuristic_score.overall_score > 0.8:
    # High quality - skip LLM evaluation
    return heuristic_score
elif heuristic_score.overall_score < 0.4:
    # Low quality - skip LLM evaluation
    return heuristic_score
else:
    # Tier 2: Embedding similarity (cheap)
    semantic_score = compute_semantic_similarity(output, golden)

    if abs(semantic_score - heuristic_score.overall_score) < 0.2:
        # Scores agree - blend and return
        return blend_scores(heuristic_score, semantic_score)
    else:
        # Tier 3: Uncertainty - use G-Eval
        return await g_eval_score(input_content, output, agent_type)
```

### 5.3 Caching and Batching

**LangChain Cache (Already Available):**
```python
from langchain.cache import SQLiteCache
from langchain.globals import set_llm_cache

set_llm_cache(SQLiteCache(database_path=".langchain.db"))
```

**Batching (Current Implementation Already Does This):**
```python
# Good: Score all criteria in parallel
tasks = [
    _score_criterion(input_content, output_str, criterion, agent_type)
    for criterion in eval_criteria
]
results = await asyncio.gather(*tasks)
```

**Result Caching:**
```python
from functools import lru_cache
import hashlib

def cache_key(input_content: str, output: str, criterion: str) -> str:
    """Generate cache key for evaluation result."""
    content = f"{input_content}|{output}|{criterion}"
    return hashlib.sha256(content.encode()).hexdigest()

# Store in Redis or SQLite for persistence
```

---

## 6. Actionable Recommendations for SkillForge

### 6.1 Immediate Improvements (Sprint 1)

**Priority 1: Self-Consistency Voting**
- File: `app/shared/services/g_eval/scorer.py`
- Add `n_samples` parameter to `_score_criterion()`
- Implement majority voting
- Calculate confidence from agreement ratio

```python
async def _score_criterion_with_consistency(
    input_content: str,
    output: str,
    criterion: str,
    agent_type: str,
    n_samples: int = 3,  # NEW: Default 3 samples
) -> CriterionScore:
    """Score with self-consistency voting."""
    tasks = [
        _score_criterion_single(input_content, output, criterion, agent_type)
        for _ in range(n_samples)
    ]
    results = await asyncio.gather(*tasks)

    # Majority voting
    scores = [r.score for r in results]
    final_score = statistics.mode(scores)

    # Confidence from agreement
    confidence = scores.count(final_score) / len(scores)

    # Use reasoning from most confident sample
    best_result = max(results, key=lambda r: r.confidence)

    return CriterionScore(
        criterion=criterion,
        score=final_score,
        normalized=(final_score - 1) / 4.0,
        confidence=confidence,
        reasoning=best_result.reasoning,
    )
```

**Priority 2: Position Bias Mitigation**
- Swap order when comparing outputs
- Average results to reduce position effects

**Priority 3: Structured Outputs**
- Replace regex parsing with Pydantic schemas
- Use LangChain `.with_structured_output()` or tool calling
- Eliminate fallback defaults

### 6.2 Short-Term Enhancements (Sprint 2-3)

**Semantic Similarity Layer**
- Add embedding-based similarity scoring
- Use as Tier 2 evaluation (between heuristic and G-Eval)
- Cache embeddings for golden examples

**Cost Optimization**
- Implement three-tier evaluation strategy
- Add result caching (Redis or SQLite)
- Track evaluation costs in LangSmith

**Enhanced Rubrics**
- Add more agent-specific rubrics
- Include example scores for calibration
- Version rubrics for A/B testing

### 6.3 Long-Term Roadmap (Phase 2)

**Multi-Model Ensemble**
- Evaluate with multiple models (GPT-4, Claude, Gemini)
- Blend scores for robustness
- Detect model-specific biases

**Automated Prompt Optimization**
- Use DSPy-style optimization
- Evolve rubrics based on human feedback
- Track prompt performance over time

**Advanced Metrics**
- RAG-specific metrics (Faithfulness, Contextual Recall)
- Agentic metrics (Task Completion, Tool Correctness)
- Custom domain metrics

---

## 7. Implementation Checklist

### Phase 1: Core Improvements (Week 1)
- [ ] Add self-consistency voting (3-5 samples)
- [ ] Implement position swapping for comparisons
- [ ] Replace regex parsing with structured outputs
- [ ] Add unit tests for new voting logic
- [ ] Measure cost impact (track LLM calls)

### Phase 2: Cost Optimization (Week 2)
- [ ] Implement three-tier evaluation strategy
- [ ] Add embedding-based similarity (Tier 2)
- [ ] Set up result caching (SQLite or Redis)
- [ ] Add evaluation cost tracking to LangSmith
- [ ] Create cost comparison dashboard

### Phase 3: Quality Enhancement (Week 3)
- [ ] Download and benchmark modern embedding models (MTEB leaderboard)
- [ ] Expand agent-specific rubrics
- [ ] Add calibration examples to prompts
- [ ] Implement multi-model ensemble (optional)
- [ ] A/B test new evaluation vs current baseline

### Phase 4: Production Hardening (Week 4)
- [ ] Add comprehensive error handling
- [ ] Implement graceful degradation (fallback to heuristic)
- [ ] Monitor evaluation latency and costs
- [ ] Document new evaluation architecture
- [ ] Create runbook for troubleshooting

---

## 8. Key Metrics to Track

**Quality Metrics:**
- Agreement rate (self-consistency voting)
- Human-AI alignment (when human labels available)
- Variance across samples (lower = more reliable)

**Cost Metrics:**
- LLM calls per evaluation
- Average cost per output scored
- Cache hit rate
- Tier distribution (% using heuristic vs embedding vs LLM)

**Performance Metrics:**
- Evaluation latency (p50, p95, p99)
- Throughput (evaluations/second)
- Error rate by tier

---

## 9. References and Further Reading

**Papers:**
- G-Eval: https://arxiv.org/abs/2303.16634
- Self-Consistency: Wang et al., 2022 (https://arxiv.org/abs/2203.11171)
- Constitutional AI: Anthropic research

**Production Systems:**
- OpenAI Evals: https://github.com/openai/evals
- Langfuse Docs: https://langfuse.com/docs
- DeepEval: https://github.com/confident-ai/deepeval
- DSPy: https://github.com/stanfordnlp/dspy

**Practitioner Guides:**
- Eugene Yan LLM Patterns: https://eugeneyan.com/writing/llm-patterns/
- MTEB Leaderboard: https://huggingface.co/spaces/mteb/leaderboard
- LangChain Evaluation: https://docs.langchain.com

**Current Implementation:**
- `/backend/app/shared/services/g_eval/scorer.py` (G-Eval core)
- `/backend/app/shared/services/quality_scorer.py` (Heuristic + G-Eval blend)
- `/backend/app/evaluation/validation/consensus.py` (Multi-annotator consensus)

---

## 10. Summary of Key Insights

### What's Working Well
- Parallel criterion scoring (efficient batching)
- Agent-specific rubrics (domain awareness)
- Hybrid approach (heuristic + G-Eval)
- Chain-of-thought prompting (reasoning transparency)

### Critical Gaps
1. **No self-consistency** - Single sample = high variance
2. **Regex parsing fragility** - Silent failures with default scores
3. **Position bias** - Order affects LLM judgments
4. **No semantic similarity** - Heuristic fallback only
5. **No cost controls** - Every evaluation = full LLM cost

### Quick Wins (High ROI)
1. Self-consistency voting (3 samples) - Better reliability
2. Structured outputs - Eliminate parsing errors
3. Embedding similarity - Fast, cheap Tier 2
4. Result caching - Avoid redundant evaluations
5. Position swapping - Reduce bias

### Long-Term Bets
1. Multi-model ensemble - Robust against model-specific biases
2. DSPy-style optimization - Automated rubric evolution
3. RAG-specific metrics - Domain-aware evaluation
4. Statistical rigor - Reproducible, calibrated scores

---

**Next Steps:**
1. Review this research with team
2. Prioritize recommendations
3. Create implementation plan
4. Set up A/B testing framework
5. Measure improvements against baseline

**Research conducted by:** AI/ML Engineer Agent
**Date:** December 17, 2025
**Version:** 1.0
