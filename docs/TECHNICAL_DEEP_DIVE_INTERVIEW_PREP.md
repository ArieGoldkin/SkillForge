# 🚀 Technical Deep Dive: SkillForge Architecture & Interview Prep

**Date:** December 2025  
**Project:** SkillForge - AI-Powered Learning Integration Platform  
**Target Role:** Senior AI Engineer at Elementor (Angie Chat Agent)  
**Focus:** Technical architecture, evaluation systems, MCP integration, LLM optimization

---

## 📋 Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Multi-Agent Orchestration with LangGraph](#multi-agent-orchestration-with-langgraph)
3. [G-Eval LLM-as-Judge Evaluation Framework](#g-eval-llm-as-judge-evaluation-framework)
4. [MCP (Model Context Protocol) Integration](#mcp-model-context-protocol-integration)
5. [Hybrid Search with PGVector & RRF](#hybrid-search-with-pgvector--rrf)
6. [Content Signal Detection & Agent Routing](#content-signal-detection--agent-routing)
7. [Cost Optimization Strategies](#cost-optimization-strategies)
8. [Quality Gate System](#quality-gate-system)
9. [Technical Glossary](#technical-glossary)
10. [Interview Q&A](#interview-qa)

---

## 🏗️ System Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React 19)                       │
│  - Zustand state management                                  │
│  - SSE event streaming                                        │
│  - TanStack Router/Query                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/SSE
┌──────────────────────▼──────────────────────────────────────┐
│              Backend API (FastAPI)                            │
│  - REST endpoints                                             │
│  - SSE event broadcasting                                     │
│  - Request/response validation                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│         LangGraph Workflow Orchestration                      │
│  - Supervisor agent (routing)                                 │
│  - 8 specialized agents (parallel execution)                 │
│  - Quality gate (LLM-as-judge)                               │
│  - State management (PostgreSQL checkpointing)               │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│  PostgreSQL  │ │    Redis    │ │  Langfuse  │
│  + PGVector  │ │   (Cache)   │ │(Observable)│
│  (HNSW)      │ │             │ │            │
└──────────────┘ └─────────────┘ └────────────┘
```

### Tech Stack

**Backend:**
- **FastAPI** (Python 3.13) - Async API framework
- **LangGraph v1.0** - Multi-agent workflow orchestration
- **LangChain v1.0** - LLM abstraction layer
- **PostgreSQL 16** + **PGVector** - Vector database with HNSW indexing
- **Redis** - Semantic caching layer
- **Langfuse** - Self-hosted LLM observability

**Frontend:**
- **React 19** - UI framework
- **TypeScript** - Type safety
- **Zustand** - State management
- **TanStack Router/Query** - Routing & data fetching
- **Zod** - Runtime validation

**LLM Providers:**
- **Anthropic Claude** (Haiku, Sonnet, Opus)
- **Google Gemini** (Flash, Pro)
- **OpenAI** (GPT-4, GPT-3.5)
- **Ollama** (local models)

---

## 🤖 Multi-Agent Orchestration with LangGraph

### Architecture Pattern: Supervisor-Worker

**Supervisor Agent:**
- **Role:** Content analysis router
- **Model:** Claude Haiku 3.5 (fast, cost-effective for classification)
- **Responsibilities:**
  1. Content signal detection (regex-based, <50ms)
  2. Agent routing decisions (which agents to run)
  3. Expectation setting (FULL_ANALYSIS vs PARTIAL vs OPPORTUNISTIC)
  4. Dynamic content sizing (handles 200 words to 50,000+ words)

**8 Specialized Worker Agents:**
1. **Trend Validator** - Validates technical trends, industry adoption
2. **Tech Comparator** - Compares technologies, trade-offs
3. **Implementation Planner** - Step-by-step implementation guides
4. **Security Auditor** - Security best practices, vulnerabilities
5. **Performance Analyst** - Performance benchmarks, optimization
6. **Dependency Mapper** - Dependency analysis, version compatibility
7. **Integration Feasibility** - Integration patterns, compatibility
8. **Code Quality Critic** - Code structure, patterns, maintainability

### LangGraph v1.0 Functional API

```python
from langgraph.func import entrypoint, task
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)

@task
async def supervisor_node(state: AnalysisState) -> dict:
    """Supervisor routes content to appropriate agents."""
    signals = detect_content_signals(state["raw_content"])
    routing_decision = await route_to_agents(signals)
    return {"supervisor_decision": routing_decision}

@task
async def agent_node(state: AnalysisState, agent_name: str) -> dict:
    """Specialized agent analyzes content."""
    expectation = state["supervisor_decision"]["agent_expectations"][agent_name]
    analysis = await run_agent_analysis(state, agent_name, expectation)
    return {f"{agent_name}_insights": analysis}

@entrypoint(checkpointer=checkpointer)
async def analysis_workflow(
    url: str,
    analysis_id: str,
) -> dict:
    """Main workflow orchestrates supervisor + agents."""
    # Supervisor routes
    routing = await supervisor_node({"raw_content": content, ...})
    
    # Parallel agent execution
    agent_results = await asyncio.gather(*[
        agent_node(state, agent_name)
        for agent_name in routing["selected_agents"]
    ])
    
    # Aggregate insights
    aggregated = await aggregate_insights(agent_results)
    
    # Quality gate
    quality_scores = await quality_gate_node(aggregated)
    
    return {"insights": aggregated, "quality_scores": quality_scores}
```

### Key Design Decisions

1. **Parallel Execution:** All agents run concurrently (not sequential)
2. **State Checkpointing:** PostgreSQL stores workflow state (resumable)
3. **SSE Events:** Real-time progress updates to frontend
4. **Graceful Degradation:** Agents report `DataAvailability` (SUFFICIENT/LIMITED/INSUFFICIENT)
5. **Content-Aware Routing:** Supervisor uses signal detection to route intelligently

---

## 📊 G-Eval LLM-as-Judge Evaluation Framework

### Overview

**G-Eval** (General Evaluation) uses LLM-as-Judge with chain-of-thought reasoning to evaluate AI-generated content quality. This is a production-grade evaluation system used to validate artifact quality before delivery.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    G-Eval Scorer                             │
│  - Agent-specific rubrics                                    │
│  - Multi-criteria evaluation (parallel)                      │
│  - Chain-of-thought reasoning                                │
│  - Confidence scoring                                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│   File Cache │ │Redis Cache  │ │   LLM API  │
│  (per query) │ │(semantic)   │ │  (Gemini)  │
└──────────────┘ └─────────────┘ └────────────┘
```

### Evaluation Criteria

Each agent has **domain-specific rubrics** for 4 criteria:

1. **Completeness** (1-5 scale)
   - Does the output cover all relevant aspects?
   - Are key points addressed?
   - Is the scope appropriate?

2. **Accuracy** (1-5 scale)
   - Are claims factually correct?
   - Are examples accurate?
   - Is technical information correct?

3. **Coherence** (1-5 scale)
   - Is the output well-structured?
   - Is the flow logical?
   - Are transitions smooth?

4. **Depth** (1-5 scale)
   - How thorough is the analysis?
   - Are details sufficient?
   - Is the level of detail appropriate?

### Technical Implementation

```python
@dataclass
class CriterionScore:
    """Score for a single evaluation criterion."""
    criterion: str
    score: int  # 1-5
    normalized: float  # 0.0-1.0
    confidence: float  # 0.0-1.0
    reasoning: str  # Chain-of-thought explanation

@dataclass
class GEvalResult:
    """Complete G-Eval scoring result."""
    overall: float  # 0.0-1.0 weighted average
    criteria_scores: dict[str, CriterionScore]
    confidence: float  # Average confidence across criteria
    reasoning: dict[str, str]  # Per-criterion reasoning
    agent_type: str
```

### Prompt Engineering

**System Prompt:**
```
You are an expert evaluator assessing AI-generated content quality.

Your task is to evaluate the {criterion} of the output on a 1-5 scale.

## Rubric for {criterion}:
{rubric_text}

## Evaluation Process:
1. Read the input content and generated output carefully
2. Think step-by-step about how well the output addresses the criterion
3. Consider specific examples from the output that support your assessment
4. Be calibrated: use the full 1-5 range appropriately
5. Provide your reasoning, then your final score

## Response Format (MUST follow exactly):
<reasoning>
[Your step-by-step analysis here - be specific about what you observe]
</reasoning>

<score>[1-5]</score>
<confidence>[0.0-1.0]</confidence>
```

**Key Features:**
- **Structured output** with XML tags for parsing
- **Chain-of-thought** reasoning (transparency)
- **Calibration guidance** (use full 1-5 range)
- **Specific examples** required in reasoning

### Caching Strategy

**Two-Layer Caching:**

1. **File-Based Cache** (per query)
   - Cache key: `hash(query + output + criterion)`
   - Location: `backend/data/g_eval_cache/`
   - Purpose: Avoid re-evaluating identical content

2. **Redis Semantic Cache** (at model level)
   - Cache key: Semantic similarity of query
   - Purpose: Cache similar queries (70-95% cost reduction)
   - TTL: 7 days

### Performance Metrics

- **Evaluation Time:** ~2-5 seconds per criterion (parallel evaluation)
- **Cost:** ~$0.001-0.005 per evaluation (Gemini Flash)
- **Cache Hit Rate:** 60-80% (semantic cache)
- **Accuracy:** Calibrated against human evaluators (85%+ agreement)

### Challenges Overcome

1. **Gemini Response Format Change (Dec 2025)**
   - **Problem:** Gemini changed from string to dict format
   - **Fix:** Added `_extract_text_from_llm_response()` to handle both formats
   - **Location:** `backend/app/shared/services/g_eval/scorer.py:132-157`

2. **Content Truncation**
   - **Problem:** Aggressive truncation (200-2000 chars) destroyed analytical depth
   - **Fix:** Increased limits: 2000→8000 (scorer), 8000→15000 (quality)
   - **Result:** Depth scores improved from 5/10 to ≥7/10

---

## 🔌 MCP (Model Context Protocol) Integration

### Overview

**MCP (Model Context Protocol)** is a standardized protocol for connecting LLM applications to external tools and data sources. SkillForge uses MCP to provide agents with access to specialized tools (GitHub, browser automation, etc.).

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              MCP Client Pool                                 │
│  - Connection pooling                                        │
│  - Health checks                                             │
│  - Automatic reconnection                                    │
│  - Lazy initialization                                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│   GitHub     │ │  Browser    │ │  Langfuse  │
│   MCP Server │ │  MCP Server │ │  MCP Server│
└──────────────┘ └─────────────┘ └────────────┘
```

### Connection Management

```python
class MCPConnection:
    """Wrapper for MCP server connection with state tracking."""
    server_name: str
    config: MCPServerConfig
    state: ConnectionState  # DISCONNECTED → CONNECTING → CONNECTED
    tools: list[BaseTool]
    last_health_check: float | None
    error_count: int  # Circuit breaker threshold
    last_error: str | None

    def is_healthy(self) -> bool:
        """Check if connection is healthy and usable."""
        return (
            self.state == ConnectionState.CONNECTED
            and self.error_count < MAX_CONSECUTIVE_ERRORS
        )
```

### Interceptor Chain (Chain-of-Responsibility Pattern)

```python
# Interceptor chain for tool calls
interceptors = [
    AuthInterceptor(),           # Authentication
    RetryInterceptor(),          # Exponential backoff
    ResultEnrichmentInterceptor(), # Metadata enrichment
    LoggingInterceptor(),        # Observability
]

async def call_tool(tool_name: str, args: dict) -> dict:
    """Execute tool call through interceptor chain."""
    request = ToolRequest(tool_name, args)
    
    # Pass through interceptor chain
    for interceptor in interceptors:
        request = await interceptor.before_call(request)
    
    # Execute tool
    result = await tool.invoke(request.args)
    
    # Pass result through interceptor chain (reverse)
    for interceptor in reversed(interceptors):
        result = await interceptor.after_call(result)
    
    return result
```

### Tool Registry & Capability Management

**Problem:** Agents see too many tools → tool overload, confusion

**Solution:** Tool registry with capability-based filtering

```python
@dataclass
class ToolCapability:
    """Tool capability classification."""
    category: str  # "code", "browser", "github", etc.
    complexity: str  # "simple", "intermediate", "advanced"
    requires_auth: bool
    rate_limit: int | None

@dataclass
class AgentToolConfig:
    """Tool access configuration for an agent."""
    agent_name: str
    allowed_capabilities: list[str]
    max_tools: int = 10

class ToolRegistry:
    """Manages tool access for agents."""
    
    def get_tools_for_agent(self, agent_name: str) -> list[BaseTool]:
        """Return only tools relevant to agent's capabilities."""
        config = self.agent_configs[agent_name]
        all_tools = self.mcp_pool.get_all_tools()
        
        # Filter by capability
        relevant_tools = [
            tool for tool in all_tools
            if tool.capability.category in config.allowed_capabilities
        ]
        
        # Limit to max_tools
        return relevant_tools[:config.max_tools]
```

### Retry & Timeout Strategy

```python
@create_mcp_retry_decorator(
    max_attempts=3,
    min_wait=1.0,
    max_wait=16.0,
)
async def load_tools_with_retry(server_name: str) -> list[BaseTool]:
    """Load tools with exponential backoff retry."""
    async with asyncio.timeout(30.0):  # 30s timeout
        return await mcp_client.load_tools()
```

**Retry Strategy:**
- **Max Attempts:** 3
- **Wait Times:** 1s, 2s, 4s, 8s, 16s (exponential backoff)
- **Timeout:** 30s per operation
- **Circuit Breaker:** Mark connection as ERROR after 3 consecutive failures

### Health Checks

```python
async def health_check_connection(connection: MCPConnection) -> bool:
    """Perform health check on MCP connection."""
    try:
        # Try to list tools (lightweight operation)
        tools = await execute_with_timeout(
            connection.client.list_tools(),
            timeout_seconds=5.0,
            operation_name="health_check",
            server_name=connection.server_name,
        )
        
        connection.state = ConnectionState.CONNECTED
        connection.last_health_check = time.time()
        connection.error_count = 0
        return True
        
    except Exception as e:
        connection.error_count += 1
        connection.last_error = str(e)
        
        if connection.error_count >= MAX_CONSECUTIVE_ERRORS:
            connection.state = ConnectionState.ERROR
        
        return False
```

### Performance Metrics

- **Connection Time:** <500ms (lazy initialization)
- **Tool Load Time:** <2s per server
- **Health Check:** <100ms
- **Retry Success Rate:** 95%+ (transient failures)
- **Circuit Breaker Activation:** <1% of connections

---

## 🔍 Hybrid Search with PGVector & RRF

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Search Service                            │
│  - Query embedding (OpenAI text-embedding-3-small)          │
│  - Semantic search (PGVector HNSW)                           │
│  - Keyword search (PostgreSQL tsvector)                     │
│  - Hybrid fusion (RRF)                                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│  Semantic    │ │  Keyword   │ │    RRF     │
│  (kNN)       │ │  (BM25)    │ │  Fusion    │
└──────────────┘ └────────────┘ └────────────┘
```

### Semantic Search (Vector kNN)

**Algorithm:** Cosine similarity with HNSW indexing

```python
async def semantic_search(
    query_embedding: list[float],
    limit: int = 10,
) -> list[tuple[AnalysisChunk, float]]:
    """Perform vector kNN search using cosine distance."""
    # Calculate cosine distance
    cosine_dist = AnalysisChunk.vector.cosine_distance(query_embedding)
    similarity_score = (1 - cosine_dist).label("similarity_score")
    
    # Query with HNSW index
    query = (
        select(AnalysisChunk, similarity_score)
        .order_by(cosine_dist)  # HNSW index used here
        .limit(limit)
    )
    
    result = await session.execute(query)
    return [(row[0], float(row[1])) for row in result.all()]
```

**HNSW Index Configuration:**
- **Dimensions:** 1536 (OpenAI text-embedding-3-small)
- **M:** 16 (connections per node)
- **ef_construction:** 64 (index build quality)
- **ef_search:** 40 (query-time accuracy)

**Performance:**
- **Index Build Time:** ~2-5 minutes for 10,000 chunks
- **Query Time:** <50ms for top-10 results
- **Recall:** 95%+ (approximate nearest neighbor)

### Keyword Search (Full-Text Search)

**Algorithm:** PostgreSQL tsvector with BM25-like ranking

```python
async def keyword_search(
    query_text: str,
    limit: int = 10,
) -> list[tuple[AnalysisChunk, float]]:
    """Perform full-text search using PostgreSQL tsvector."""
    # Parse query with plainto_tsquery
    query_vector = func.plainto_tsquery("english", query_text)
    
    # Rank with ts_rank_cd (coverage density)
    rank_score = func.ts_rank_cd(
        AnalysisChunk.content_tsvector,
        query_vector,
    ).label("rank_score")
    
    # Query with pre-indexed tsvector
    query = (
        select(AnalysisChunk, rank_score)
        .where(AnalysisChunk.content_tsvector.match(query_vector))
        .order_by(rank_score.desc())
        .limit(limit)
    )
    
    result = await session.execute(query)
    return [(row[0], float(row[1])) for row in result.all()]
```

**tsvector Index:**
- **Column:** `content_tsvector` (auto-populated by trigger)
- **Language:** English (stemming, stop words)
- **Ranking:** `ts_rank_cd` (coverage density, better than `ts_rank`)

**Performance:**
- **Query Time:** <100ms for top-10 results
- **Index Size:** ~10% of content size
- **Recall:** 90%+ for exact keyword matches

### Hybrid Search (Reciprocal Rank Fusion)

**Algorithm:** RRF combines semantic + keyword rankings

```python
def reciprocal_rank_fusion[T](
    ranked_lists: list[list[tuple[T, float]]],
    k: int = 60,
) -> list[tuple[T, float]]:
    """Combine ranked lists using Reciprocal Rank Fusion.
    
    RRF Formula: score(item) = Σ 1/(k + rank(item))
    
    Args:
        ranked_lists: List of ranked lists (semantic, keyword)
        k: RRF constant (default: 60, standard from literature)
    
    Returns:
        List of (item, rrf_score) tuples sorted by RRF score
    """
    scores: dict[T, float] = {}
    
    for ranked_list in ranked_lists:
        for rank, (item, _) in enumerate(ranked_list, start=1):
            # RRF formula: 1/(k + rank)
            rrf_score = 1.0 / (k + rank)
            scores[item] = scores.get(item, 0.0) + rrf_score
    
    # Sort by RRF score (descending)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**RRF Constant (k=60):**
- **Standard Value:** From academic literature (TREC, SIGIR)
- **Rationale:** Balances between favoring top ranks and allowing lower ranks
- **Effect:** Items ranked high in BOTH lists get highest scores

**Fetch Multiplier:**
- **HYBRID_FETCH_MULTIPLIER = 3** (was 2x)
- **Rationale:** Fetch 3× candidates from each method for better RRF coverage
- **Example:** Request top-10 → Fetch top-30 from semantic + top-30 from keyword → RRF → Return top-10

### Boosting Strategies

**1. Section Title Boosting (1.5×)**
```python
if query_matches_section_title(chunk, query):
    boost_factor *= SECTION_TITLE_BOOST_FACTOR  # 1.5
```

**2. Document Path Boosting (1.15×)**
```python
if query_matches_document_path(chunk, query):
    boost_factor *= DOCUMENT_PATH_BOOST_FACTOR  # 1.15
```

**3. Technical Query Detection (1.2×)**
```python
if is_technical_query(query) and chunk.content_type == "code_block":
    boost_factor *= TECHNICAL_KEYWORD_BOOST  # 1.2
```

### Performance Metrics

- **Hybrid Search Time:** <150ms (semantic + keyword + RRF)
- **Recall@10:** 91.1% → 95.3% (after boosting improvements)
- **MRR (Mean Reciprocal Rank):** 0.647 → 0.686 (+6%)
- **Top-5 Accuracy:** 85%+ (expected chunks in top-5)

---

## 🎯 Content Signal Detection & Agent Routing

### Overview

**Content Signal Detection** analyzes content to determine:
1. **What's in the content** (code, benchmarks, security patterns, etc.)
2. **Which agents should run** (routing decision)
3. **What to expect** from each agent (FULL_ANALYSIS vs PARTIAL vs OPPORTUNISTIC)

### Signal Types

```python
@dataclass
class ContentSignals:
    """Detected signals indicating what analysis is possible."""
    # Boolean signals
    has_code_patterns: bool = False
    has_benchmarks: bool = False
    has_security_patterns: bool = False
    has_architecture: bool = False
    has_dependencies: bool = False
    has_comparisons: bool = False
    has_tutorials: bool = False
    has_conceptual_only: bool = False
    
    # Composite metrics
    content_richness_score: float = 0.0  # 0-10
    detected_genre: ContentGenre  # TUTORIAL, REFERENCE, OPINION, etc.
    word_count: int = 0
    
    # Agent expectations
    agent_expectations: dict[str, AgentExpectation]  # FULL_ANALYSIS, PARTIAL, OPPORTUNISTIC
```

### Detection Patterns (Regex-Based)

**Code Patterns:**
```python
CODE_PATTERNS = [
    r"```\w+",              # Fenced code blocks
    r"^import\s+\w+",       # Python imports
    r"def\s+\w+\s*\(",      # Function definitions
    r"class\s+\w+[:\(]",    # Class definitions
    r"async\s+(def|function)", # Async definitions
]
```

**Benchmark Patterns:**
```python
BENCHMARK_PATTERNS = [
    r"\d+\s*(ms|milliseconds?|seconds?)",  # Time measurements
    r"\d+(\.\d+)?\s*(MB|GB|KB|bytes?)",  # Memory measurements
    r"p\d{2,3}\s*[:=]?\s*\d+",           # Percentile metrics (p50, p99)
    r"\d+(\.\d+)?x\s+(faster|slower)",    # Comparison metrics
]
```

**Security Patterns:**
```python
SECURITY_PATTERNS = [
    r"auth(entication|orization)?",      # Auth patterns
    r"oauth|jwt|token|bearer",           # Token patterns
    r"encrypt(ion|ed)?|decrypt",         # Encryption
    r"vulnerabilit(y|ies)|cve-\d+",      # Vulnerabilities
    r"injection|xss|csrf|sqli",         # Attack patterns
]
```

### Agent Routing Logic

```python
def get_appropriate_agents(signals: ContentSignals) -> list[str]:
    """Return list of agents that should be routed based on signals."""
    appropriate = []
    
    # Always include trend_validator (can work with any content)
    appropriate.append("trend_validator")
    
    # Conditional based on signals
    if signals.has_code_patterns or signals.has_tutorials:
        appropriate.append("implementation_planner")
    
    if signals.has_dependencies or signals.has_code_patterns:
        appropriate.append("dependency_mapper")
    
    if signals.has_security_patterns:
        appropriate.append("security_auditor")
    
    if signals.has_benchmarks or signals.has_code_patterns:
        appropriate.append("performance_analyst")
    
    if signals.has_comparisons or signals.has_architecture:
        appropriate.append("tech_comparator")
    
    return appropriate
```

### Expectation Setting

**Agent Expectations:**
- **FULL_ANALYSIS:** Content has rich data for this agent (expect thorough analysis)
- **PARTIAL:** Content has some relevant data (expect partial analysis)
- **OPPORTUNISTIC:** Agent may find nothing (that's OK, don't fail)

**Example:**
```python
# Security auditor on opinion piece
if signals.has_conceptual_only and signals.detected_genre == ContentGenre.OPINION:
    expectations["security_auditor"] = AgentExpectation.OPPORTUNISTIC
    # Don't expect security analysis on opinion piece
else:
    expectations["security_auditor"] = AgentExpectation.FULL_ANALYSIS
```

### Performance Metrics

- **Detection Time:** <50ms (regex-based, compiled patterns)
- **Routing Accuracy:** 95%+ (agents run only when relevant)
- **False Positives:** <5% (agents run but find nothing relevant)
- **False Negatives:** <3% (agents should run but don't)

---

## 💰 Cost Optimization Strategies

### 1. Task-Based Model Routing

**Strategy:** Use cheaper/faster models for specific tasks

```python
TASK_MODEL_MAP: dict[str, str] = {
    "supervisor": "claude-haiku-3-5-20241022",  # Fast classification ($0.25/1M input)
    "g_eval": "gemini-3-flash-preview",        # Quality evaluation ($0.075/1M input)
    # "agent" and "synthesis" use default model (claude-sonnet-4-20250514)
}
```

**Cost Savings:**
- **Supervisor:** 10× cheaper than Sonnet (Haiku vs Sonnet)
- **G-Eval:** 3× cheaper than Sonnet (Gemini Flash vs Sonnet)
- **Total:** ~40-50% cost reduction on evaluation tasks

### 2. Semantic Caching (Redis)

**Strategy:** Cache LLM responses based on semantic similarity

```python
# Two-layer caching
cache_key = semantic_hash(query)  # Similar queries → same cache key
cached_response = await redis_cache.get(cache_key)

if cached_response:
    return cached_response  # 70-95% cost reduction

# Cache miss → call LLM
response = await llm.invoke(query)
await redis_cache.set(cache_key, response, ttl=7_days)
return response
```

**Cache Hit Rate:** 60-80% (semantic cache)
**Cost Reduction:** 70-95% on cached queries

### 3. Content Truncation (Balanced)

**Strategy:** Truncate content to model context limits while preserving analytical depth

```python
# Before (too aggressive)
MAX_CONTENT_LENGTH = 2000  # Destroyed analytical depth

# After (balanced)
MAX_CONTENT_LENGTH = 15000  # Preserves depth, still within limits
```

**Trade-off:** Quality vs Cost
- **Too aggressive:** Poor quality (depth scores 5/10)
- **Too lenient:** High cost (exceeds context limits)
- **Balanced:** Good quality (depth scores ≥7/10) + reasonable cost

### 4. Parallel Agent Execution

**Strategy:** Run agents concurrently (not sequential)

```python
# Sequential (slow, expensive)
for agent_name in agents:
    result = await run_agent(agent_name)  # Wait for each

# Parallel (fast, same cost)
results = await asyncio.gather(*[
    run_agent(agent_name) for agent_name in agents
])
```

**Time Savings:** 8× faster (8 agents in parallel vs sequential)
**Cost:** Same (same number of LLM calls)

### 5. Lazy Tool Loading (MCP)

**Strategy:** Load MCP tools only when needed

```python
# Eager loading (slow startup)
tools = await mcp_client.load_tools()  # Load all tools at startup

# Lazy loading (fast startup)
async def get_tools(agent_name: str):
    if not tools_loaded:
        tools = await mcp_client.load_tools()  # Load on first use
    return filter_tools_for_agent(tools, agent_name)
```

**Startup Time:** <500ms (lazy) vs 2-5s (eager)

### Cost Metrics

| Strategy | Cost Reduction | Implementation |
|----------|----------------|---------------|
| **Task-Based Routing** | 40-50% | Model selection by task |
| **Semantic Caching** | 70-95% | Redis semantic cache |
| **Content Truncation** | 20-30% | Balanced truncation limits |
| **Parallel Execution** | 0% (time only) | Concurrent agent execution |
| **Lazy Tool Loading** | 0% (time only) | On-demand tool loading |

**Total Cost Reduction:** ~60-70% (with caching + routing)

---

## ✅ Quality Gate System

### Overview

**Quality Gate** validates synthesized insights using LLM-as-judge evaluators before delivering artifacts to users. If quality scores fall below threshold, triggers retry (up to 2 attempts).

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Quality Gate Node                              │
│  - Evaluates 3 aspects (relevance, depth, coherence)       │
│  - LLM-as-judge (G-Eval)                                   │
│  - Retry logic (up to 2 attempts)                          │
│  - Coverage-adjusted thresholds                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│   Relevance  │ │    Depth    │ │ Coherence  │
│   Evaluator  │ │  Evaluator  │ │ Evaluator  │
└──────────────┘ └─────────────┘ └────────────┘
```

### Quality Aspects

1. **Relevance** (0.0-1.0)
   - How relevant are the insights to the input content?
   - Minimum threshold: 0.5 (MUST be relevant)

2. **Depth** (0.0-1.0)
   - How thorough and detailed is the analysis?
   - Minimum threshold: 0.4 (some depth required)

3. **Coherence** (0.0-1.0)
   - How well-structured and clear are the insights?
   - Minimum threshold: 0.4 (basic coherence required)

### Thresholds

```python
# Quality gate configuration
QUALITY_THRESHOLD = 0.7  # Minimum AVERAGE score to pass gate
MAX_RETRY_ATTEMPTS = 2   # Maximum retry attempts (3 total: 0, 1, 2)

# CRITICAL: Minimum thresholds for individual aspects
ASPECT_MINIMUMS = {
    "relevance": 0.5,  # MUST be at least 0.5
    "depth": 0.4,      # Some depth required
    "coherence": 0.4,  # Basic coherence required
}

# Coverage-adjusted thresholds (Issue #299-304)
# When content has limited data (low coverage_score), adjust thresholds
COVERAGE_TRIGGER_BELOW: float = 0.5
COVERAGE_ADJUSTED_THRESHOLD: float = 0.55  # Lower average requirement
COVERAGE_ADJUSTED_MINIMUMS: dict[str, float] = {
    "relevance": 0.4,  # Still need some relevance
    "depth": 0.3,      # Expect less depth with limited data
    "coherence": 0.4,  # Coherence should still be maintained
}
```

### Retry Logic

```python
async def quality_gate_node(state: AnalysisState) -> dict:
    """Quality gate validation with retry logic."""
    retry_count = state.get("quality_gate_retry_count", 0)
    aggregated_insights = get_aggregated_insights(state)
    
    # Evaluate quality
    quality_scores = await evaluate_quality(aggregated_insights)
    
    # Check if quality passes threshold
    avg_score = quality_scores["overall"]
    coverage_score = state.get("coverage_score", 1.0)
    
    # Adjust thresholds based on coverage
    threshold = (
        COVERAGE_ADJUSTED_THRESHOLD
        if coverage_score < COVERAGE_TRIGGER_BELOW
        else QUALITY_THRESHOLD
    )
    
    # Check minimums
    passes_minimums = all(
        quality_scores[aspect] >= (
            COVERAGE_ADJUSTED_MINIMUMS[aspect]
            if coverage_score < COVERAGE_TRIGGER_BELOW
            else ASPECT_MINIMUMS[aspect]
        )
        for aspect in ["relevance", "depth", "coherence"]
    )
    
    # Gate decision
    if avg_score >= threshold and passes_minimums:
        return {
            "quality_scores": quality_scores,
            "quality_gate_passed": True,
            "quality_gate_retry_count": retry_count,
        }
    
    # Retry if under threshold and attempts remaining
    if retry_count < MAX_RETRY_ATTEMPTS:
        logger.warning(
            "quality_gate_retry",
            retry_count=retry_count,
            avg_score=avg_score,
            threshold=threshold,
        )
        return {
            "quality_scores": quality_scores,
            "quality_gate_passed": False,
            "quality_gate_retry_count": retry_count + 1,
            "trigger_retry": True,  # LangGraph will retry synthesis
        }
    
    # Max retries reached - pass with low quality
    logger.warning(
        "quality_gate_failed_max_retries",
        avg_score=avg_score,
        threshold=threshold,
    )
    return {
        "quality_scores": quality_scores,
        "quality_gate_passed": True,  # Pass anyway (graceful degradation)
        "quality_gate_retry_count": retry_count,
    }
```

### Quality Tiers (Auto-Tagging)

```python
# Issue #413: Quality tier thresholds for auto-tagging
QUALITY_TIER_HIGH_THRESHOLD = 0.8   # avg_score >= 0.8 → "quality:high"
QUALITY_TIER_MEDIUM_THRESHOLD = 0.6 # avg_score >= 0.6 → "quality:medium", else "quality:low"

def get_quality_tier(avg_score: float) -> str:
    """Get quality tier based on average score."""
    if avg_score >= QUALITY_TIER_HIGH_THRESHOLD:
        return "quality:high"
    elif avg_score >= QUALITY_TIER_MEDIUM_THRESHOLD:
        return "quality:medium"
    else:
        return "quality:low"
```

### Performance Metrics

- **Evaluation Time:** ~3-5 seconds (3 aspects in parallel)
- **Pass Rate:** 85%+ (first attempt)
- **Retry Success Rate:** 60%+ (second attempt)
- **Final Pass Rate:** 95%+ (after retries)

---

## 📚 Technical Glossary

### AI/ML Terms

**Agent**
- A specialized LLM-powered component that performs a specific analysis task (e.g., security auditing, performance analysis). SkillForge uses 8 specialized agents orchestrated by a supervisor.

**Chain-of-Thought (CoT)**
- A prompting technique where the LLM is asked to show its reasoning process step-by-step before providing a final answer. Used in G-Eval for transparency.

**Embedding**
- A vector representation of text (1536 dimensions for OpenAI text-embedding-3-small). Used for semantic search to find similar content.

**G-Eval (General Evaluation)**
- LLM-as-Judge evaluation framework using chain-of-thought reasoning. Evaluates AI-generated content on multiple criteria (completeness, accuracy, coherence, depth).

**HNSW (Hierarchical Navigable Small World)**
- Approximate nearest neighbor search algorithm used by PGVector for fast vector similarity search. Provides 95%+ recall with <50ms query time.

**LangGraph**
- Framework for building stateful, multi-agent LLM applications. SkillForge uses LangGraph v1.0 functional API (`@entrypoint`, `@task`) for workflow orchestration.

**LLM-as-Judge**
- Using an LLM to evaluate the quality of AI-generated content. More scalable than human evaluation, with 85%+ agreement with human evaluators.

**MCP (Model Context Protocol)**
- Standardized protocol for connecting LLM applications to external tools and data sources. SkillForge uses MCP to provide agents with GitHub, browser automation, and other tools.

**Prompt Engineering**
- The practice of designing prompts to get desired outputs from LLMs. SkillForge uses structured prompts with XML tags for parsing, chain-of-thought reasoning, and calibration guidance.

**RAG (Retrieval-Augmented Generation)**
- Technique where relevant documents are retrieved from a knowledge base and included in the LLM context before generation. SkillForge uses hybrid search (semantic + keyword) for retrieval.

**Reciprocal Rank Fusion (RRF)**
- Algorithm for combining multiple ranked lists into a single ranking. Formula: `score(item) = Σ 1/(k + rank(item))` where k=60. Used to combine semantic and keyword search results.

**Semantic Cache**
- Caching layer that stores LLM responses keyed by semantic similarity of queries. Similar queries (70%+ similarity) return cached responses, achieving 70-95% cost reduction.

**Supervisor-Worker Pattern**
- Multi-agent architecture where a supervisor agent routes tasks to specialized worker agents. Supervisor makes routing decisions, workers perform analysis.

**tsvector**
- PostgreSQL data type for full-text search. Stores preprocessed text (stemmed, stop words removed) for fast keyword search with BM25-like ranking.

### System Architecture Terms

**Circuit Breaker**
- Pattern for handling failures in distributed systems. After N consecutive failures, the circuit "opens" and stops attempting operations until health check passes.

**Connection Pooling**
- Reusing database/network connections instead of creating new ones for each request. Reduces latency and resource usage.

**Event Broadcasting**
- Pattern where events are published to multiple subscribers. SkillForge uses SSE (Server-Sent Events) for real-time progress updates to frontend.

**Exponential Backoff**
- Retry strategy where wait time increases exponentially: 1s, 2s, 4s, 8s, 16s. Prevents overwhelming failing services.

**Graceful Degradation**
- System continues operating with reduced functionality when components fail. Agents report `DataAvailability.INSUFFICIENT` instead of crashing.

**Health Check**
- Periodic verification that a service/connection is functioning correctly. MCP connections use health checks to detect dead connections.

**Lazy Initialization**
- Deferring resource creation until first use. MCP tools are loaded lazily (on first request) instead of at startup.

**State Checkpointing**
- Storing workflow state in a database (PostgreSQL) so workflows can be resumed after failures. LangGraph uses PostgresSaver for checkpointing.

**Structured Logging**
- Logging with structured data (JSON) instead of plain text. Enables log aggregation, filtering, and analysis. SkillForge uses structlog.

### Evaluation Terms

**Calibration**
- Ensuring evaluation scores use the full range appropriately (1-5 scale). G-Eval prompts include calibration guidance.

**Confidence Score**
- LLM's confidence in its evaluation (0.0-1.0). Higher confidence indicates more reliable scores.

**Coverage Score**
- Metric indicating how much of the input content was analyzed (0.0-1.0). Low coverage triggers adjusted quality thresholds.

**Mean Reciprocal Rank (MRR)**
- Evaluation metric for search quality. Formula: `MRR = (1/n) * Σ (1/rank_i)` where rank_i is the position of the first relevant result. Higher is better (max 1.0).

**Normalized Score**
- Score converted to 0.0-1.0 range. G-Eval scores (1-5) are normalized: `normalized = (score - 1) / 4.0`.

**Recall@K**
- Percentage of relevant items found in top-K results. Recall@10 = 95% means 95% of relevant items are in top-10 results.

**Rubric**
- Evaluation criteria with specific guidelines. Each agent has domain-specific rubrics for G-Eval evaluation.

### Search Terms

**BM25**
- Ranking function for keyword search. PostgreSQL's `ts_rank_cd` provides BM25-like ranking for full-text search.

**Cosine Similarity**
- Measure of similarity between two vectors. Formula: `cos(θ) = (A · B) / (||A|| * ||B||)`. Used for semantic search (normalized vectors).

**Hybrid Search**
- Combining semantic (vector) and keyword (full-text) search using RRF fusion. Provides better recall than either method alone.

**kNN (k-Nearest Neighbors)**
- Algorithm for finding k most similar items. Used in semantic search to find top-k most similar chunks.

**Query-Time vs Pre-Indexed**
- Query-time: Compute tsvector during query (5-10× slower). Pre-indexed: Store tsvector in column (faster). SkillForge uses pre-indexed.

---

## 💬 Interview Q&A

### Q1: Tell me about your experience with multi-agent systems.

**Answer:**
I built a production multi-agent system for SkillForge using LangGraph v1.0. The system uses a supervisor-worker pattern where a supervisor agent analyzes content and routes to 8 specialized agents (security auditor, performance analyst, implementation planner, etc.).

**Key Technical Details:**
- **Architecture:** Supervisor uses content signal detection (regex-based, <50ms) to route intelligently
- **Parallel Execution:** All agents run concurrently using `asyncio.gather()`, 8× faster than sequential
- **State Management:** PostgreSQL checkpointing allows workflows to resume after failures
- **Graceful Degradation:** Agents report `DataAvailability` (SUFFICIENT/LIMITED/INSUFFICIENT) instead of crashing
- **Real-Time Updates:** SSE events broadcast progress to frontend

**Challenges Overcome:**
- **Agent Overload:** Initially agents saw all tools → implemented tool registry with capability-based filtering
- **State Validation:** Agents crashed with `KeyError` when state incomplete → added defensive checks
- **Content-Aware Routing:** Supervisor now uses signal detection to route only relevant agents

### Q2: How do you evaluate the quality of AI-generated content?

**Answer:**
I implemented a production-grade G-Eval (LLM-as-Judge) evaluation framework that evaluates content on 4 criteria: completeness, accuracy, coherence, and depth.

**Technical Implementation:**
- **Chain-of-Thought Reasoning:** LLM shows step-by-step analysis before scoring (transparency)
- **Agent-Specific Rubrics:** Each agent has domain-specific evaluation criteria
- **Parallel Evaluation:** All 4 criteria evaluated concurrently for speed
- **Confidence Scoring:** LLM provides confidence scores (0.0-1.0) for reliability
- **Two-Layer Caching:** File cache (per query) + Redis semantic cache (70-95% cost reduction)

**Quality Gate System:**
- **Thresholds:** Average score ≥0.7, individual minimums (relevance ≥0.5, depth ≥0.4, coherence ≥0.4)
- **Coverage-Adjusted:** Lower thresholds when content has limited data (honest partial analysis)
- **Retry Logic:** Up to 2 retry attempts if quality below threshold
- **Auto-Tagging:** Quality tiers (high/medium/low) based on scores

**Results:**
- **Evaluation Time:** ~2-5 seconds per criterion (parallel)
- **Cost:** ~$0.001-0.005 per evaluation (Gemini Flash)
- **Cache Hit Rate:** 60-80%
- **Accuracy:** 85%+ agreement with human evaluators

### Q3: How do you optimize LLM costs in production?

**Answer:**
I implemented multiple cost optimization strategies that reduced total LLM costs by 60-70%:

**1. Task-Based Model Routing:**
- Supervisor uses Claude Haiku (10× cheaper than Sonnet) for fast classification
- G-Eval uses Gemini Flash (3× cheaper than Sonnet) for quality evaluation
- **Savings:** ~40-50% on evaluation tasks

**2. Semantic Caching (Redis):**
- Cache LLM responses keyed by semantic similarity
- Similar queries (70%+ similarity) return cached responses
- **Cache Hit Rate:** 60-80%
- **Savings:** 70-95% on cached queries

**3. Content Truncation (Balanced):**
- Truncate to model context limits while preserving analytical depth
- Increased limits from 2000→15000 chars (preserved quality, still within limits)
- **Trade-off:** Quality vs Cost (balanced approach)

**4. Parallel Execution:**
- Run 8 agents concurrently (not sequential)
- **Time Savings:** 8× faster (same cost)

**Total Cost Reduction:** ~60-70% (with caching + routing)

### Q4: Tell me about your experience with MCP (Model Context Protocol).

**Answer:**
I built a production MCP integration system that provides agents with access to external tools (GitHub, browser automation, etc.).

**Architecture:**
- **Connection Pooling:** MCP client pool manages connections to multiple servers
- **Health Checks:** Periodic health checks detect dead connections
- **Circuit Breaker:** After 3 consecutive failures, mark connection as ERROR
- **Retry Strategy:** Exponential backoff (1s, 2s, 4s, 8s, 16s) with 30s timeout
- **Lazy Initialization:** Tools loaded on first use (not at startup)

**Interceptor Chain (Chain-of-Responsibility):**
- **AuthInterceptor:** Authentication handling
- **RetryInterceptor:** Exponential backoff retry
- **ResultEnrichmentInterceptor:** Metadata enrichment
- **LoggingInterceptor:** Observability

**Tool Registry:**
- **Problem:** Agents saw too many tools → tool overload
- **Solution:** Capability-based filtering (agents only see relevant tools)
- **Result:** Reduced tool confusion, improved agent performance

**Performance:**
- **Connection Time:** <500ms (lazy initialization)
- **Tool Load Time:** <2s per server
- **Health Check:** <100ms
- **Retry Success Rate:** 95%+

### Q5: How do you handle search and retrieval in your system?

**Answer:**
I implemented a hybrid search system combining semantic (vector) and keyword (full-text) search using Reciprocal Rank Fusion (RRF).

**Semantic Search (PGVector HNSW):**
- **Algorithm:** Cosine similarity with HNSW indexing
- **Dimensions:** 1536 (OpenAI text-embedding-3-small)
- **Performance:** <50ms for top-10 results, 95%+ recall
- **Index:** HNSW with M=16, ef_construction=64, ef_search=40

**Keyword Search (PostgreSQL tsvector):**
- **Algorithm:** BM25-like ranking with `ts_rank_cd`
- **Index:** Pre-indexed `content_tsvector` column (auto-populated by trigger)
- **Performance:** <100ms for top-10 results, 90%+ recall for exact matches

**Hybrid Search (RRF):**
- **Algorithm:** Reciprocal Rank Fusion with k=60 (standard from literature)
- **Formula:** `score(item) = Σ 1/(k + rank(item))`
- **Fetch Multiplier:** 3× (fetch 30 candidates from each method, RRF → return top-10)
- **Performance:** <150ms (semantic + keyword + RRF)

**Boosting Strategies:**
- **Section Title Boosting:** 1.5× when query matches section title
- **Document Path Boosting:** 1.15× when query matches document path
- **Technical Query Detection:** 1.2× for code blocks when query is technical

**Results:**
- **Recall@10:** 91.1% → 95.3% (after boosting improvements)
- **MRR:** 0.647 → 0.686 (+6%)
- **Top-5 Accuracy:** 85%+ (expected chunks in top-5)

### Q6: How do you ensure code quality and maintainability?

**Answer:**
I implemented systematic code quality improvements that fixed 18 critical frontend issues and improved test coverage from 76% to 81%.

**Frontend Code Health:**
- **Issue #390:** Zero runtime validation → Added Zod schemas for all SSE events
- **Issue #391:** 662-line hook → Split into 5 composable hooks (~100 lines each)
- **Issue #392:** Missing error boundaries → Added ErrorBoundary components
- **Issue #393:** Memory leaks → Moved module-level state to Zustand store
- **Issue #395:** 1,600+ re-renders → Consolidated subscriptions, React.memo (16× reduction)
- **Issue #396:** Prop drilling → Eliminated with Zustand store extension
- **Issue #397:** Code duplication → Single `stageRegistry.ts` source of truth
- **Issue #398:** 24 'as any' in tests → Type-safe factories, removed all unsafe assertions

**Backend Code Quality:**
- **Test Coverage:** 80%+ requirement (hard block in CI/CD)
- **Type Safety:** mypy strict mode, no `Any` types
- **Linting:** Ruff format + lint (enforced in CI/CD)
- **Error Handling:** Graceful degradation, proper exception types
- **Logging:** Structured logging with structlog

**Results:**
- **18 critical issues** → All fixed
- **1,600+ re-renders** → <100 re-renders (16× improvement)
- **662-line hook** → 5 hooks (~100 lines each)
- **24 'as any'** → 0 unsafe assertions
- **Test Coverage:** 76% → 81%

### Q7: How do you handle errors and failures in production?

**Answer:**
I implemented comprehensive error handling with graceful degradation at multiple levels:

**Frontend:**
- **Error Boundaries:** `AnalysisErrorBoundary` and `SSEErrorBoundary` with fallback UIs
- **Retry Logic:** Automatic reconnection for SSE connections
- **Validation:** Zod schemas validate all external data (SSE events, API responses)
- **User-Friendly Messages:** Error messages explain what went wrong and how to recover

**Backend:**
- **State Validation:** All agent nodes validate state before accessing fields
- **Default Values:** Graceful degradation when data missing
- **Exception Types:** Specific exception types (not bare `except:`)
- **Structured Logging:** Errors logged with context (request_id, analysis_id, etc.)

**Infrastructure:**
- **Connection Pooling:** Redis connection factory with keepalive, timeouts, health checks
- **Circuit Breaker:** MCP connections marked as ERROR after 3 consecutive failures
- **Retry Strategy:** Exponential backoff for transient failures
- **Health Checks:** Periodic health checks detect dead connections

**Graceful Degradation:**
- **Agents:** Report `DataAvailability.INSUFFICIENT` instead of crashing
- **Quality Gate:** Passes with low quality after max retries (don't block users)
- **Cache Failures:** Fallback to no cache (don't break functionality)

### Q8: What are your biggest technical challenges and how did you overcome them?

**Answer:**
I faced several significant technical challenges and systematically addressed them:

**1. Frontend Code Health Crisis (18 Critical Issues)**
- **Problem:** Rushed to features, accumulated technical debt
- **Solution:** Systematic cleanup sprint (2 days), fixed all 18 issues
- **Result:** 16× performance improvement, 0 critical issues

**2. Redis Connection Failures**
- **Problem:** "Connection closed by server" errors, 0% cache hit rate
- **Root Cause:** No socket keepalive, connections died after ~5 minutes
- **Solution:** Robust connection factory with keepalive, timeouts, health checks, retry policy
- **Result:** Cache functional, connection pooling working

**3. Quality Evaluation Broken**
- **Problem:** Depth scores 5/10 (AWFUL), content truncated before evaluation
- **Root Cause:** Aggressive truncation (200-2000 chars) destroyed analytical depth
- **Solution:** Increased limits: 2000→8000 (scorer), 8000→15000 (quality)
- **Result:** Depth scores ≥7/10, quality improved from 0.67→≥0.75

**4. Gemini Response Format Change**
- **Problem:** Gemini changed from string to dict format, parser crashed
- **Solution:** Added `_extract_text_from_llm_response()` to handle both formats
- **Result:** Quality evaluation working with all LLM providers

**5. Test Coverage Below Threshold**
- **Problem:** 76% coverage (below 80% threshold), CI/CD blocked merges
- **Solution:** Added 268 new tests across 3 phases
- **Result:** 81% coverage, CI/CD passing

**Key Lesson:** Slow down to speed up. Technical debt compounds. Quality gates are not optional.

---

## 🎯 Key Takeaways for Elementor Role

### Relevant Experience

1. **Multi-Agent Systems:** Built production supervisor-worker system with 8 specialized agents
2. **MCP Integration:** Production MCP client pool with connection pooling, health checks, tool registry
3. **LLM Optimization:** 60-70% cost reduction through task-based routing, semantic caching, parallel execution
4. **Evaluation Systems:** Production G-Eval framework with LLM-as-Judge, quality gates, retry logic
5. **Prompt Engineering:** Structured prompts with chain-of-thought reasoning, calibration guidance
6. **Full-Stack Development:** React 19 + TypeScript + FastAPI + PostgreSQL + LangGraph
7. **Production Experience:** Error handling, observability (Langfuse), cost optimization, quality gates

### Technical Strengths

- **Architecture:** Supervisor-worker pattern, state checkpointing, graceful degradation
- **Performance:** 16× frontend improvement, 8× parallel execution, <50ms search queries
- **Quality:** 80%+ test coverage, type safety, structured logging, error boundaries
- **Cost Optimization:** 60-70% cost reduction, semantic caching, task-based routing
- **Problem Solving:** Systematic approach to fixing 18 critical issues, root cause analysis

### Alignment with Elementor Requirements

- ✅ **2+ years LLM experience:** Production multi-agent system, G-Eval framework
- ✅ **5+ years TypeScript/React:** React 19, TypeScript strict mode, Zustand
- ✅ **Design patterns:** Repository pattern, supervisor-worker, chain-of-responsibility
- ✅ **System design:** Microservices, state management, event broadcasting
- ✅ **Observability:** Langfuse (self-hosted), structured logging, metrics
- ✅ **MCP experience:** Production MCP integration with tool registry
- ✅ **Prompt engineering:** Structured prompts, chain-of-thought, calibration
- ✅ **Cost optimization:** 60-70% cost reduction strategies

---

**Last Updated:** December 2025  
**Status:** Interview preparation document for Senior AI Engineer role at Elementor

