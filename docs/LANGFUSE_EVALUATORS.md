# Langfuse LLM-as-a-Judge Evaluators

## Overview

LLM-as-a-Judge evaluators use large language models (LLMs) to automatically assess the quality of AI-generated responses across multiple dimensions. Instead of manual review or rule-based heuristics, these evaluators leverage the reasoning capabilities of advanced models like Gemini 2.5 Flash to score responses on criteria such as hallucination, correctness, relevance, helpfulness, and faithfulness.

**Benefits:**
- **Automated Quality Monitoring**: Continuous evaluation of all trace executions
- **Scalable Assessment**: Evaluates every response without manual intervention
- **Multi-Dimensional Scoring**: Provides nuanced quality metrics beyond simple pass/fail
- **Production Observability**: Real-time quality insights in Langfuse dashboard

## Configured Evaluators

We have deployed **5 production evaluators** in our Langfuse instance:

### 1. Hallucination Detection
**Purpose**: Detects when LLM outputs contain information not grounded in the provided context or source documents.

**Scoring Criteria:**
- 0.0 = Severe hallucination (fabricated facts)
- 0.5 = Minor unsupported claims
- 1.0 = Fully grounded in context

**Use Case**: Critical for RAG pipelines where responses must be backed by retrieved chunks.

---

### 2. Correctness
**Purpose**: Validates factual accuracy of responses against ground truth or expected answers.

**Scoring Criteria:**
- 0.0 = Factually incorrect
- 0.5 = Partially correct
- 1.0 = Completely accurate

**Use Case**: Ensures LLM outputs align with verified information.

---

### 3. Relevance
**Purpose**: Measures how relevant the response is to the user's original query or prompt.

**Scoring Criteria:**
- 0.0 = Off-topic or irrelevant
- 0.5 = Partially relevant
- 1.0 = Highly relevant and on-topic

**Use Case**: Prevents context drift and ensures focused responses.

---

### 4. Helpfulness
**Purpose**: Assesses whether the response is actionable and useful to the user.

**Scoring Criteria:**
- 0.0 = Unhelpful or vague
- 0.5 = Somewhat helpful
- 1.0 = Extremely helpful and actionable

**Use Case**: Measures user-centric quality beyond technical correctness.

---

### 5. Faithfulness (RAGAS)
**Purpose**: Checks if the response remains faithful to the source documents without adding unsupported interpretations.

**Scoring Criteria:**
- 0.0 = Contradicts source documents
- 0.5 = Partially faithful with some additions
- 1.0 = Fully faithful to sources

**Use Case**: Ensures RAG responses don't misrepresent retrieved content.

**Framework**: Based on RAGAS (Retrieval Augmented Generation Assessment) methodology.

---

## Configuration Details

| Parameter | Value |
|-----------|-------|
| **Model** | `google/gemini-2.5-flash` |
| **Target** | Trace level (evaluates entire execution) |
| **Project** | SkillForge Backend |
| **Execution** | Automatic on trace completion |
| **Sampling** | 100% of traces (all evaluators run on every trace) |

**Why Gemini 2.5 Flash?**
- Low latency (~1-2s per evaluation)
- Cost-effective for high-volume evaluation
- Strong reasoning capabilities for nuanced scoring
- Supports structured JSON outputs

---

## Viewing Results in Langfuse UI

### Dashboard Access
1. Navigate to Langfuse dashboard: `http://localhost:3000` (local) or production URL
2. Select **SkillForge Backend** project
3. Go to **Traces** tab

### Trace-Level Scores
Each trace displays evaluator scores in the trace detail view:

```
Trace: analysis-workflow-abc123
├── Hallucination: 0.95 ✓
├── Correctness: 0.88 ✓
├── Relevance: 1.00 ✓
├── Helpfulness: 0.92 ✓
└── Faithfulness: 0.90 ✓
```

### Filtering by Score
Use Langfuse filters to identify quality issues:
- **Low Hallucination Scores** (`< 0.7`): Review for factual errors
- **Low Relevance Scores** (`< 0.6`): Check for context drift
- **Low Faithfulness Scores** (`< 0.8`): Investigate RAG retrieval quality

### Aggregate Metrics
Navigate to **Evaluations** tab for aggregate statistics:
- Average scores per evaluator
- Score distributions (histogram)
- Trends over time
- Correlation analysis between evaluators

---

## Integration with Golden Dataset

Our **98-document golden dataset** serves as the evaluation baseline:

### Dataset Composition
- **98 Analyses**: Completed technical content analyses
- **98 Artifacts**: Generated implementation guides
- **415 Chunks**: Semantic search chunks with embeddings
- **Content Types**: 76 articles, 19 tutorials, 3 research papers
- **Topics**: RAG, LangGraph, Prompt Engineering, API Design, Testing

### Evaluation Workflow

```
1. User submits URL for analysis
   ↓
2. LangGraph workflow processes content
   ↓
3. Trace sent to Langfuse with:
   - Input query
   - Retrieved chunks (context)
   - Generated response
   - Source documents
   ↓
4. LLM-as-a-Judge evaluators score trace:
   - Hallucination → Checks response vs retrieved chunks
   - Correctness → Validates facts against golden dataset
   - Relevance → Measures alignment with user query
   - Helpfulness → Assesses actionability
   - Faithfulness → Ensures source fidelity
   ↓
5. Scores displayed in Langfuse UI
```

### Golden Dataset Benefits
- **Baseline Truth**: Known-good analyses for comparison
- **Regression Detection**: Identify quality degradation over time
- **Evaluator Calibration**: Validate evaluator accuracy against human-reviewed content
- **Test Coverage**: Evaluate new prompts/models against proven dataset

### Example Evaluation

**Scenario**: User asks about RAG retrieval strategies

**Golden Dataset**: Contains 12 RAG-related articles

**Evaluation**:
1. **Relevance**: 0.95 (query matches RAG topic)
2. **Correctness**: 0.88 (facts verified against golden articles)
3. **Hallucination**: 0.92 (no unsupported claims)
4. **Faithfulness**: 0.90 (response grounded in retrieved chunks)
5. **Helpfulness**: 0.85 (provides actionable strategies)

**Outcome**: High-quality response confirmed by automated evaluation

---

## Maintenance & Monitoring

### Regular Tasks
1. **Weekly**: Review low-scoring traces in Langfuse UI
2. **Monthly**: Analyze evaluator score trends
3. **Quarterly**: Validate evaluators against human review sample (10-20 traces)

### Alert Thresholds
Set up alerts for quality degradation:
- **Hallucination** < 0.70 → Critical (high risk of misinformation)
- **Correctness** < 0.60 → High (factual errors)
- **Relevance** < 0.50 → Medium (context drift)
- **Helpfulness** < 0.50 → Medium (poor user experience)
- **Faithfulness** < 0.75 → High (source misrepresentation)

### Backup & Recovery
Golden dataset is backed up via:
```bash
cd backend
poetry run python scripts/backup_golden_dataset.py backup
```

Restore evaluators by re-importing golden dataset:
```bash
poetry run python scripts/backup_golden_dataset.py restore --replace
```

---

## References

- **Langfuse Documentation**: https://langfuse.com/docs/scores/model-based-evals
- **RAGAS Framework**: https://docs.ragas.io/en/latest/
- **LLM-as-a-Judge Paper**: "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena"
- **Gemini API**: https://ai.google.dev/gemini-api/docs

---

**Last Updated**: December 2025
**Project**: SkillForge Backend
**Version**: 1.0.0
