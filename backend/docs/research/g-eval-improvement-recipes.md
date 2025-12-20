# G-Eval Improvement Recipes

**Quick reference for implementing latest LLM evaluation best practices**

---

## Recipe 1: Self-Consistency Voting

**Problem:** Single LLM call = high variance, unreliable scores
**Solution:** Generate 3-5 samples, use majority voting
**Cost:** 3-5x LLM calls
**Benefit:** Higher reliability, confidence estimates

### Implementation

```python
import statistics
from typing import List

async def _score_criterion_with_consistency(
    input_content: str,
    output: str,
    criterion: str,
    agent_type: str,
    n_samples: int = 3,
    temperature: float = 0.7,
) -> CriterionScore:
    """Score with self-consistency voting.

    Args:
        input_content: Original input/task
        output: Generated output to evaluate
        criterion: Evaluation criterion
        agent_type: Agent type for rubric selection
        n_samples: Number of samples for voting (default: 3)
        temperature: Sampling temperature (default: 0.7)

    Returns:
        CriterionScore with majority vote and confidence
    """
    model = get_chat_model()
    rubric_text = format_rubric_for_prompt(agent_type, criterion)

    system_prompt = G_EVAL_SYSTEM_PROMPT.format(
        criterion=criterion,
        rubric_text=rubric_text,
    )

    user_prompt = G_EVAL_USER_PROMPT.format(
        input_content=input_content[:2000],
        output=output[:3000],
        criterion=criterion,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    # Generate multiple samples
    tasks = [
        model.ainvoke(messages, temperature=temperature)
        for _ in range(n_samples)
    ]

    responses = await asyncio.gather(*tasks)
    results = [_parse_g_eval_response(r.content, criterion) for r in responses]

    # Majority voting
    scores = [r.score for r in results]
    final_score = statistics.mode(scores)

    # Confidence = agreement ratio
    confidence = scores.count(final_score) / len(scores)

    # Use reasoning from most confident sample
    best_result = max(results, key=lambda r: r.confidence)

    logger.info(
        "self_consistency_voting",
        criterion=criterion,
        n_samples=n_samples,
        scores=scores,
        final_score=final_score,
        agreement_rate=confidence,
    )

    return CriterionScore(
        criterion=criterion,
        score=final_score,
        normalized=(final_score - 1) / 4.0,
        confidence=confidence,
        reasoning=best_result.reasoning,
    )
```

**Usage:**
```python
# Update g_eval_score() to use consistency voting
async def g_eval_score(
    input_content: str,
    output: dict[str, Any] | str,
    agent_type: str,
    criteria: list[str] | None = None,
    n_samples: int = 3,  # NEW: Enable self-consistency
) -> GEvalResult:
    # ... existing code ...

    # Score all criteria with consistency voting
    tasks = [
        _score_criterion_with_consistency(
            input_content, output_str, criterion, agent_type, n_samples
        )
        for criterion in eval_criteria
    ]

    results = await asyncio.gather(*tasks)
    # ... rest of existing code ...
```

---

## Recipe 2: Structured Outputs (No Regex Parsing)

**Problem:** Regex parsing fails silently, defaults to fallback scores
**Solution:** Use Pydantic schemas with LangChain structured outputs
**Cost:** No additional cost
**Benefit:** Guaranteed valid scores, better errors

### Implementation

```python
from pydantic import BaseModel, Field

class EvaluationResponse(BaseModel):
    """Structured G-Eval response."""
    reasoning: str = Field(description="Step-by-step analysis of the criterion")
    score: int = Field(ge=1, le=5, description="Score from 1 (worst) to 5 (best)")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this score")

async def _score_criterion_structured(
    input_content: str,
    output: str,
    criterion: str,
    agent_type: str,
) -> CriterionScore:
    """Score using structured outputs (no regex parsing)."""
    model = get_chat_model()
    rubric_text = format_rubric_for_prompt(agent_type, criterion)

    # Updated prompt for structured output
    system_prompt = f"""You are an expert evaluator assessing AI-generated content quality.

Your task is to evaluate the {criterion} of the output on a 1-5 scale.

## Rubric for {criterion}:
{rubric_text}

## Evaluation Process:
1. Read the input content and generated output carefully
2. Think step-by-step about how well the output addresses the criterion
3. Consider specific examples from the output that support your assessment
4. Be calibrated: use the full 1-5 range appropriately
5. Provide your reasoning, score, and confidence

Respond using the structured format provided."""

    user_prompt = f"""## Task/Input:
{input_content[:2000]}

## Generated Output to Evaluate:
{output[:3000]}

Evaluate the {criterion} of this output using the rubric provided."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    try:
        # Use structured output - no parsing needed!
        response = await model.with_structured_output(EvaluationResponse).ainvoke(messages)

        # Normalize score to 0-1 range
        normalized = (response.score - 1) / 4.0

        return CriterionScore(
            criterion=criterion,
            score=response.score,
            normalized=normalized,
            confidence=response.confidence,
            reasoning=response.reasoning[:500],
        )

    except Exception as e:
        logger.exception("structured_scoring_error", criterion=criterion, error=str(e))
        # Return neutral score on error
        return CriterionScore(
            criterion=criterion,
            score=3,
            normalized=0.5,
            confidence=0.0,
            reasoning=f"Error during evaluation: {str(e)}",
        )
```

**Alternative: Tool Calling (for Claude)**
```python
tools = [{
    "name": "submit_evaluation",
    "description": "Submit evaluation score for the criterion",
    "input_schema": {
        "type": "object",
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "Step-by-step analysis"
            },
            "score": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5,
                "description": "Score from 1 (worst) to 5 (best)"
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Confidence in this score"
            }
        },
        "required": ["reasoning", "score", "confidence"]
    }
}]

response = await model.ainvoke(messages, tools=tools, tool_choice={"type": "tool", "name": "submit_evaluation"})
tool_call = response.tool_calls[0]
args = tool_call["args"]

return CriterionScore(
    criterion=criterion,
    score=args["score"],
    normalized=(args["score"] - 1) / 4.0,
    confidence=args["confidence"],
    reasoning=args["reasoning"][:500],
)
```

---

## Recipe 3: Three-Tier Evaluation (Cost Optimization)

**Problem:** Every evaluation = expensive LLM call
**Solution:** Filter with heuristics, use embeddings, LLM only when uncertain
**Cost:** 60-80% reduction in LLM calls
**Benefit:** Faster, cheaper, same quality

### Implementation

```python
from sentence_transformers import SentenceTransformer, util

# Global embedding model (load once)
_embedding_model = None

def get_embedding_model():
    """Lazy load embedding model."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
    return _embedding_model

def compute_semantic_similarity(
    output: dict[str, Any],
    golden_output: dict[str, Any],
) -> float:
    """Compute semantic similarity using embeddings.

    Args:
        output: Agent output to evaluate
        golden_output: Golden example for comparison

    Returns:
        Similarity score 0.0-1.0
    """
    import json

    model = get_embedding_model()

    # Convert to text
    output_text = json.dumps(output, indent=2, default=str)
    golden_text = json.dumps(golden_output, indent=2, default=str)

    # Encode
    emb1 = model.encode(output_text, convert_to_tensor=True)
    emb2 = model.encode(golden_text, convert_to_tensor=True)

    # Cosine similarity
    similarity = util.cos_sim(emb1, emb2).item()

    return float(similarity)

async def score_with_three_tier(
    output: dict[str, Any],
    input_content: str,
    golden_example: dict[str, Any] | None,
    agent_type: str,
    schema_class: type[BaseModel] | None = None,
) -> GEvalQualityScore:
    """Three-tier evaluation: heuristic -> embedding -> LLM.

    Tier 1: Heuristic scoring (fast, free)
    Tier 2: Embedding similarity (fast, cheap)
    Tier 3: G-Eval LLM scoring (slow, expensive)

    Args:
        output: Agent output to evaluate
        input_content: Original input/task
        golden_example: Golden example for comparison
        agent_type: Agent type
        schema_class: Optional schema for validation

    Returns:
        GEvalQualityScore with tier information
    """
    # Tier 1: Heuristic scoring (always run)
    heuristic_score = score_output_quality(
        output=output,
        golden_example=golden_example,
        agent_type=agent_type,
        schema_class=schema_class,
    )

    # High confidence from heuristic? Skip deeper evaluation
    if heuristic_score.overall_score > 0.85:
        logger.info(
            "tier1_confident_high",
            agent_type=agent_type,
            score=heuristic_score.overall_score,
            tier="heuristic_only",
        )
        return GEvalQualityScore(
            completeness_score=heuristic_score.completeness_score,
            accuracy_score=heuristic_score.accuracy_score,
            detail_score=heuristic_score.detail_score,
            structure_score=heuristic_score.structure_score,
            overall_score=heuristic_score.overall_score,
            token_count=heuristic_score.token_count,
            reasoning={"method": "heuristic_high_confidence"},
            confidence=0.8,
            scoring_method="tier1_heuristic",
        )

    # Very low heuristic score? Skip deeper evaluation
    if heuristic_score.overall_score < 0.3:
        logger.info(
            "tier1_confident_low",
            agent_type=agent_type,
            score=heuristic_score.overall_score,
            tier="heuristic_only",
        )
        return GEvalQualityScore(
            completeness_score=heuristic_score.completeness_score,
            accuracy_score=heuristic_score.accuracy_score,
            detail_score=heuristic_score.detail_score,
            structure_score=heuristic_score.structure_score,
            overall_score=heuristic_score.overall_score,
            token_count=heuristic_score.token_count,
            reasoning={"method": "heuristic_low_confidence"},
            confidence=0.8,
            scoring_method="tier1_heuristic",
        )

    # Tier 2: Embedding similarity (if golden example available)
    if golden_example and golden_example.get("output_example"):
        semantic_score = compute_semantic_similarity(
            output,
            golden_example["output_example"],
        )

        # Heuristic and embedding agree?
        if abs(semantic_score - heuristic_score.overall_score) < 0.15:
            # Agreement - blend and return
            blended_score = (heuristic_score.overall_score + semantic_score) / 2

            logger.info(
                "tier2_agreement",
                agent_type=agent_type,
                heuristic=heuristic_score.overall_score,
                semantic=semantic_score,
                blended=blended_score,
                tier="heuristic_embedding",
            )

            return GEvalQualityScore(
                completeness_score=heuristic_score.completeness_score,
                accuracy_score=semantic_score,  # Use semantic for accuracy
                detail_score=heuristic_score.detail_score,
                structure_score=heuristic_score.structure_score,
                overall_score=blended_score,
                token_count=heuristic_score.token_count,
                reasoning={"method": "heuristic_embedding_agreement"},
                confidence=0.85,
                scoring_method="tier2_embedding",
            )

    # Tier 3: Uncertainty - use G-Eval
    logger.info(
        "tier3_uncertainty",
        agent_type=agent_type,
        heuristic=heuristic_score.overall_score,
        tier="g_eval_deep",
    )

    config = GEvalConfig(schema_class=schema_class)
    return await score_output_quality_g_eval(
        output=output,
        input_content=input_content,
        agent_type=agent_type,
        config=config,
    )
```

---

## Recipe 4: Position Bias Mitigation

**Problem:** LLMs favor first option in comparisons
**Solution:** Evaluate both orders, average results
**Cost:** 2x LLM calls for comparisons
**Benefit:** Fairer, unbiased evaluations

### Implementation

```python
async def compare_outputs_unbiased(
    input_content: str,
    output_a: dict[str, Any],
    output_b: dict[str, Any],
    criterion: str,
    agent_type: str,
) -> tuple[float, float]:
    """Compare two outputs with position bias mitigation.

    Args:
        input_content: Original task/input
        output_a: First output to compare
        output_b: Second output to compare
        criterion: Evaluation criterion
        agent_type: Agent type

    Returns:
        Tuple of (score_a, score_b) with bias mitigation
    """
    import json

    output_a_str = json.dumps(output_a, indent=2, default=str)
    output_b_str = json.dumps(output_b, indent=2, default=str)

    # Score A vs B (A first)
    prompt_ab = f"""Compare these two outputs for {criterion}.

## Task:
{input_content[:1500]}

## Output A:
{output_a_str[:2000]}

## Output B:
{output_b_str[:2000]}

Which output better satisfies the {criterion} criterion? Rate each 1-5."""

    # Score B vs A (B first)
    prompt_ba = f"""Compare these two outputs for {criterion}.

## Task:
{input_content[:1500]}

## Output B:
{output_b_str[:2000]}

## Output A:
{output_a_str[:2000]}

Which output better satisfies the {criterion} criterion? Rate each 1-5."""

    # Evaluate both orders
    score_ab_a = await _score_criterion(input_content, output_a_str, criterion, agent_type)
    score_ab_b = await _score_criterion(input_content, output_b_str, criterion, agent_type)
    score_ba_a = await _score_criterion(input_content, output_a_str, criterion, agent_type)
    score_ba_b = await _score_criterion(input_content, output_b_str, criterion, agent_type)

    # Average across both orderings
    final_score_a = (score_ab_a.normalized + score_ba_a.normalized) / 2
    final_score_b = (score_ab_b.normalized + score_ba_b.normalized) / 2

    logger.info(
        "position_bias_mitigation",
        criterion=criterion,
        score_a_ab=score_ab_a.normalized,
        score_a_ba=score_ba_a.normalized,
        score_b_ab=score_ab_b.normalized,
        score_b_ba=score_ba_b.normalized,
        final_a=final_score_a,
        final_b=final_score_b,
    )

    return (final_score_a, final_score_b)
```

---

## Recipe 5: Result Caching

**Problem:** Re-evaluating same outputs wastes money
**Solution:** Cache evaluation results by content hash
**Cost:** Storage overhead (minimal)
**Benefit:** Avoid redundant LLM calls

### Implementation

```python
import hashlib
import json
from typing import Optional

# In-memory cache (use Redis in production)
_evaluation_cache: dict[str, GEvalResult] = {}

def _cache_key(input_content: str, output: str, agent_type: str, criteria: list[str]) -> str:
    """Generate cache key for evaluation result.

    Args:
        input_content: Original input
        output: Output being evaluated
        agent_type: Agent type
        criteria: List of criteria

    Returns:
        SHA256 hash as cache key
    """
    content = f"{input_content}|{output}|{agent_type}|{','.join(sorted(criteria))}"
    return hashlib.sha256(content.encode()).hexdigest()

async def g_eval_score_cached(
    input_content: str,
    output: dict[str, Any] | str,
    agent_type: str,
    criteria: list[str] | None = None,
) -> GEvalResult:
    """Score with caching to avoid redundant evaluations.

    Args:
        input_content: Original input/task
        output: Generated output to evaluate
        agent_type: Agent type
        criteria: Optional criteria list

    Returns:
        GEvalResult (cached or fresh)
    """
    # Convert output to string
    if isinstance(output, dict):
        output_str = json.dumps(output, indent=2, default=str)
    else:
        output_str = str(output)

    # Get criteria
    config = get_agent_rubrics(agent_type)
    eval_criteria = criteria or config.get("criteria", ["completeness", "accuracy", "coherence", "depth"])

    # Check cache
    cache_key = _cache_key(input_content, output_str, agent_type, eval_criteria)

    if cache_key in _evaluation_cache:
        logger.info(
            "g_eval_cache_hit",
            agent_type=agent_type,
            cache_key=cache_key[:16],
        )
        return _evaluation_cache[cache_key]

    # Cache miss - compute score
    logger.info(
        "g_eval_cache_miss",
        agent_type=agent_type,
        cache_key=cache_key[:16],
    )

    result = await g_eval_score(input_content, output, agent_type, eval_criteria)

    # Cache result
    _evaluation_cache[cache_key] = result

    return result
```

**Production Redis Version:**
```python
import redis
import pickle

redis_client = redis.Redis(host='localhost', port=6379, db=0)

async def g_eval_score_redis_cached(
    input_content: str,
    output: dict[str, Any] | str,
    agent_type: str,
    criteria: list[str] | None = None,
    ttl: int = 86400,  # 24 hours
) -> GEvalResult:
    """Score with Redis caching."""
    # ... (same cache key generation) ...

    # Check Redis
    cached = redis_client.get(cache_key)
    if cached:
        logger.info("redis_cache_hit", cache_key=cache_key[:16])
        return pickle.loads(cached)

    # Compute score
    result = await g_eval_score(input_content, output, agent_type, eval_criteria)

    # Cache in Redis with TTL
    redis_client.setex(cache_key, ttl, pickle.dumps(result))

    return result
```

---

## Recipe 6: Modern Embedding Models (MTEB Leaderboard)

**Problem:** Using outdated embeddings (BERT 2018)
**Solution:** Use top models from MTEB leaderboard
**Cost:** One-time model download (~400MB)
**Benefit:** Better semantic similarity accuracy

### Implementation

```python
from sentence_transformers import SentenceTransformer

# Top models from MTEB leaderboard (December 2024)
# Check https://huggingface.co/spaces/mteb/leaderboard for latest

RECOMMENDED_MODELS = {
    "general": "sentence-transformers/all-mpnet-base-v2",  # Balanced
    "fast": "sentence-transformers/all-MiniLM-L6-v2",      # Small, fast
    "accuracy": "BAAI/bge-large-en-v1.5",                  # Large, accurate
}

class EmbeddingService:
    """Service for computing embeddings."""

    def __init__(self, model_name: str = "general"):
        """Initialize embedding model.

        Args:
            model_name: One of "general", "fast", "accuracy"
        """
        model_path = RECOMMENDED_MODELS.get(model_name, model_name)
        self.model = SentenceTransformer(model_path)

    def encode(self, text: str) -> list[float]:
        """Encode text to embedding vector.

        Args:
            text: Text to encode

        Returns:
            Embedding vector
        """
        return self.model.encode(text, convert_to_tensor=False).tolist()

    def similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score 0.0-1.0
        """
        from sentence_transformers import util

        emb1 = self.model.encode(text1, convert_to_tensor=True)
        emb2 = self.model.encode(text2, convert_to_tensor=True)

        return util.cos_sim(emb1, emb2).item()

# Singleton instance
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """Get global embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(model_name="general")
    return _embedding_service
```

---

## Quick Comparison Table

| Recipe | Cost Impact | Accuracy Gain | Implementation Effort | Priority |
|--------|-------------|---------------|----------------------|----------|
| Self-Consistency | +200-400% | +15-25% | Medium | HIGH |
| Structured Outputs | 0% | +5-10% (fewer errors) | Low | HIGH |
| Three-Tier Eval | -60-80% | 0% (same quality) | Medium | HIGH |
| Position Bias Fix | +100% | +5-15% | Low | MEDIUM |
| Result Caching | -50-90% | 0% | Low | HIGH |
| Modern Embeddings | 0% | +10-20% (semantic) | Low | MEDIUM |

---

## Testing New Implementations

```python
import pytest

@pytest.mark.asyncio
async def test_self_consistency_voting():
    """Test self-consistency produces stable results."""
    input_content = "Compare React vs Vue for our project"
    output = {
        "primary_tech": "React",
        "recommendation": "Use React for better ecosystem",
        "confidence_score": 0.85,
    }

    # Run 3 times, should get consistent scores
    results = []
    for _ in range(3):
        score = await _score_criterion_with_consistency(
            input_content, json.dumps(output), "completeness", "tech_comparator", n_samples=3
        )
        results.append(score.score)

    # Variance should be low (scores should be similar across runs)
    variance = statistics.variance(results)
    assert variance <= 1.0, f"High variance: {variance}, scores: {results}"


@pytest.mark.asyncio
async def test_three_tier_cost_savings():
    """Test three-tier evaluation reduces LLM calls."""
    # Mock heuristic high score
    with patch('app.shared.services.quality_scorer.score_output_quality') as mock_heuristic:
        mock_heuristic.return_value = QualityScore(
            completeness_score=0.9,
            accuracy_score=0.9,
            detail_score=0.9,
            structure_score=0.9,
            overall_score=0.9,
            token_count=100,
        )

        with patch('app.shared.services.g_eval.g_eval_score') as mock_g_eval:
            result = await score_with_three_tier(
                output={"test": "data"},
                input_content="test input",
                golden_example=None,
                agent_type="tech_comparator",
            )

            # Should NOT call G-Eval (Tier 1 confident)
            assert mock_g_eval.call_count == 0
            assert result.scoring_method == "tier1_heuristic"
```

---

**Next Steps:**
1. Choose recipes based on priority table
2. Implement in test branch
3. A/B test against current baseline
4. Measure cost and quality impact
5. Roll out to production

**See also:** `/backend/docs/research/llm-evaluation-best-practices-2025.md` for full research details.
