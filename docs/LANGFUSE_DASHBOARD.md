# Langfuse Dashboard Usage Guide

**For:** SkillForge Developers
**Last Updated:** December 19, 2025
**Self-Hosted Instance:** http://localhost:3000

## Overview

SkillForge uses **self-hosted Langfuse** for comprehensive LLM observability, replacing the deprecated LangSmith service. Langfuse provides end-to-end tracing, quality scoring, prompt management, and cost tracking for all AI-powered workflows.

**Why Langfuse?**
- Free and open-source (no usage limits)
- Self-hosted (complete data control)
- Production-ready observability (tracing, metrics, scoring)
- Native prompt versioning and management
- LLM-as-Judge integration for automated quality evaluation

**Integration Status:** ✅ Complete (December 2025 migration)

---

## Quick Start

### Access the Dashboard

1. **Start Langfuse services:**
   ```bash
   # From project root
   docker-compose up -d langfuse-web langfuse-worker

   # Verify health
   curl http://localhost:3000/api/health
   # Expected: {"status":"ok"}
   ```

2. **Open dashboard:**
   - URL: http://localhost:3000
   - Login credentials (development):
     - Email: `dev@skillforge.local`
     - Password: `skillforge-dev-password`

3. **Select SkillForge project** from the project dropdown

### Environment Variables

Required in `backend/.env`:

```bash
# Langfuse Configuration
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...    # From UI: Project Settings → API Keys
LANGFUSE_SECRET_KEY=sk-lf-...    # From UI: Project Settings → API Keys
```

**Get API Keys:**
1. Login to http://localhost:3000
2. Navigate to **Project Settings → API Keys**
3. Copy both Public Key and Secret Key
4. Update `.env` file

---

## Dashboard Views

### 1. Traces View

**Purpose:** Monitor all LLM calls, workflow executions, and agent activity in real-time.

**What it shows:**
- Complete execution hierarchy (workflow → nodes → LLM calls)
- Latency per operation
- Token usage and costs per trace
- Status (success/error)
- Metadata (analysis_id, content_type, url)

**How to use:**

```plaintext
FILTER BY SESSION:
1. Click "Add Filter"
2. Select "Session ID"
3. Enter: analysis-<uuid>
   → Shows all traces for a specific analysis

FILTER BY TAGS:
- Tag: "quality-gate" → Quality gate evaluations only
- Tag: "workflow" → Top-level workflow traces
- Tag: "quality:high" → High-quality artifacts
- Tag: "quality:low" → Low-quality artifacts needing review
- Tag: "gate:passed" → Analyses that passed quality gate
- Tag: "gate:failed" → Failed quality gates

FILTER BY METADATA:
- metadata.analysis_id = "<uuid>" → Specific analysis
- metadata.content_type = "article" → All article analyses
- metadata.retry_count > 0 → Quality gate retries
```

**Common Queries:**

| Use Case | Filter |
|----------|--------|
| All traces for analysis `abc-123` | `session_id = "analysis-abc-123"` |
| Failed quality gates | `tags contains "gate:failed"` |
| High-quality artifacts | `tags contains "quality:high"` |
| Expensive analyses (>$0.10) | `total_cost > 0.10` |
| Slow analyses (>60s) | `latency > 60000` (milliseconds) |

**Trace Hierarchy Example:**
```
analysis_workflow (45.2s, $0.15)
├── supervisor_node (1.2s)
│   └── metadata: {selected_agents: 5}
├── tech_comparator_agent (8.3s, $0.045)
│   ├── retrieval (0.5s)
│   └── generation (7.8s, $0.045)
├── security_auditor_agent (9.1s, $0.050)
├── aggregate_findings (2.1s, $0.015)
└── quality_gate_node (3.5s, $0.040)
    └── scores: {relevance: 0.85, depth: 0.78, coherence: 0.82}
```

---

### 2. Sessions View

**Purpose:** Group related traces by analysis to see complete user journeys.

**What it shows:**
- All traces grouped by `session_id`
- Session-level aggregated metrics (total cost, duration, trace count)
- Session metadata (analysis_id, user_id)

**How to use:**

```plaintext
SESSION NAMING CONVENTION:
- Format: "analysis-<uuid>"
- Maps to: AnalysisID from database
- Groups: All workflow/agent traces for one analysis

FIND A SESSION:
1. Click on any session row
2. See all traces in that session
3. View aggregated costs and latency
```

**Use Cases:**
- **Cost analysis per analysis:** See total LLM spend for each content analysis
- **User journey tracking:** Follow multi-turn conversations (future: Socratic tutor)
- **Performance debugging:** Identify slow sessions for optimization

---

### 3. Scores View

**Purpose:** Track quality metrics from LLM-as-Judge evaluations (G-Eval).

**What it shows:**
- Quality scores per trace (relevance, depth, coherence)
- Average quality score distribution
- Score trends over time

**Quality Scoring in SkillForge:**

| Score Name | Range | What it measures |
|------------|-------|------------------|
| `quality_relevance` | 0-10 | How relevant insights are to input content |
| `quality_depth` | 0-10 | Thoroughness and detail of analysis |
| `quality_coherence` | 0-10 | Structure, clarity, logical flow |
| `quality_avg` | 0-10 | Average of above three scores |

**Auto-Applied Tags:**

| Tag | Condition | Meaning |
|-----|-----------|---------|
| `quality:high` | avg ≥ 7.5 | Excellent artifact quality |
| `quality:medium` | 5.0 ≤ avg < 7.5 | Acceptable quality |
| `quality:low` | avg < 5.0 | Poor quality, needs review |
| `gate:passed` | avg ≥ 7.0 | Passed quality gate threshold |
| `gate:failed` | avg < 7.0 | Failed quality gate, triggered retry |

**How to use:**

```plaintext
FILTER LOW-QUALITY ARTIFACTS:
1. Go to Scores view
2. Filter: score_name = "quality_avg", value < 5.0
3. Click trace_id to investigate why quality is low

TRACK QUALITY TRENDS:
1. Select date range (last 7/30 days)
2. View average quality_avg over time
3. Identify quality degradation or improvements
```

---

### 4. Prompts View

**Purpose:** Version control and manage LLM prompts in production.

**What it shows:**
- All prompts stored in Langfuse
- Version history per prompt
- Active version labels (production, staging, draft)

**SkillForge Prompts:**

| Prompt Name | Purpose | Location |
|-------------|---------|----------|
| Agent system prompts | Tech Comparator, Security Auditor, etc. | Future: Migrate from code |
| G-Eval criteria | Quality evaluation rubrics | Future: Store in Langfuse |
| Synthesis templates | Aggregation/artifact generation | Future: Version control |

**How to use:**

```plaintext
CREATE PROMPT (via UI):
1. Click "New Prompt"
2. Name: "security_auditor_v2"
3. Content: System prompt text with {{variables}}
4. Label: "staging"
5. Save

FETCH PROMPT (via Python):
from langfuse import Langfuse
langfuse = Langfuse()
prompt = langfuse.get_prompt("security_auditor_v2", label="production")
compiled = prompt.compile(variables={"context": "..."})

UPDATE PROMPT:
1. Edit existing prompt
2. Save creates new version automatically
3. Update label to promote staging → production
```

**Best Practice:** Always version prompts in Langfuse instead of hardcoding in Python.

---

### 5. Datasets View

**Purpose:** Manage test datasets for LLM evaluation and regression testing.

**What it shows:**
- Test datasets with input/expected output pairs
- Dataset runs (evaluation results)
- Accuracy metrics per dataset

**SkillForge Usage:**

| Dataset Name | Purpose | Status |
|--------------|---------|--------|
| `golden_dataset` | 98 curated technical documents | ✅ Synced from backup |
| `quality_eval_test` | Quality gate test cases | Future |
| `retrieval_benchmark` | Hybrid search evaluation | Future |

**Sync Golden Dataset to Langfuse:**

```bash
# From backend/
poetry run python scripts/sync_golden_dataset_to_langfuse.py

# Verifies:
# - 98 analyses uploaded as dataset items
# - Input: Original URL
# - Expected output: Generated artifact content
# - Metadata: analysis_id, content_type, quality_scores
```

**Use Cases:**
- **Regression testing:** Detect quality degradation after prompt changes
- **A/B testing:** Compare two prompt versions on same dataset
- **Benchmarking:** Track retrieval accuracy over time

---

## Common Workflows

### Workflow 1: Debug a Slow Analysis

**Scenario:** User reports analysis took 5 minutes instead of usual 45 seconds.

**Steps:**

1. **Find the trace:**
   - Go to **Sessions** view
   - Search by `analysis_id` metadata
   - Or filter `session_id = "analysis-<uuid>"`

2. **Analyze latency breakdown:**
   - Click on session to expand traces
   - Look for slowest operations (red/orange latency bars)
   - Check if one agent is bottleneck

3. **Investigate root cause:**
   - Click into slow trace (e.g., `tech_comparator_agent`)
   - Check generation latency vs retrieval latency
   - Review metadata for clues (token count, chunk count)

4. **Common issues:**
   - **Slow LLM generation:** Large input tokens → compress context
   - **Slow retrieval:** Too many chunks → adjust top_k
   - **Quality gate retries:** Low scores → improve prompts

### Workflow 2: Investigate Quality Issues

**Scenario:** Multiple analyses tagged `quality:low` in past 24 hours.

**Steps:**

1. **Filter low-quality traces:**
   - Go to **Traces** view
   - Add filter: `tags contains "quality:low"`
   - Date range: Last 24 hours

2. **Review quality scores:**
   - Click on a trace
   - Go to **Scores** tab
   - Check which aspect failed:
     - Low `quality_relevance` → Off-topic content
     - Low `quality_depth` → Shallow analysis
     - Low `quality_coherence` → Structural issues

3. **Compare with high-quality:**
   - Filter `tags contains "quality:high"`
   - Compare input content characteristics
   - Identify patterns (content_type, source, length)

4. **Root cause investigation:**
   - **Content issue:** Input content was poor quality
   - **Retrieval issue:** Retrieved irrelevant chunks
   - **Prompt issue:** Agent prompt needs tuning
   - **Model issue:** Wrong model/temperature settings

### Workflow 3: Review Low-Quality Artifacts

**Scenario:** You want to manually review artifacts that failed quality gate.

**Steps:**

1. **Query failed gates:**
   - **Traces** view → Filter: `tags contains "gate:failed"`
   - Sort by date (newest first)

2. **Export for review:**
   - Click each trace
   - Copy `analysis_id` from metadata
   - Query database:
     ```sql
     SELECT id, url, content_type, status
     FROM analyses
     WHERE id IN ('uuid1', 'uuid2', ...);
     ```

3. **Human annotation (future):**
   - Use Langfuse annotation queue
   - Mark thumbs up/down on quality
   - Provide feedback comments
   - Feed back to training data

### Workflow 4: Compare Prompt Versions

**Scenario:** Testing new security auditor prompt for better vulnerability detection.

**Steps:**

1. **Create prompt versions:**
   - **Prompts** view → Edit "security_auditor"
   - Save new version with label "staging"
   - Keep old version labeled "production"

2. **Run A/B test:**
   ```python
   # In code, randomly select version
   import random
   label = random.choice(["production", "staging"])
   prompt = langfuse.get_prompt("security_auditor", label=label)

   # Track which version was used
   update_current_trace(metadata={"prompt_version": prompt.version})
   ```

3. **Compare results in dashboard:**
   - **Traces** view → Filter by `metadata.prompt_version`
   - Group by version: v1 vs v2
   - Compare:
     - Average `quality_depth` score
     - Average cost per trace
     - Average latency

4. **Promote winner:**
   - If v2 outperforms, change label to "production"
   - Immediately affects all future analyses

---

## Performance Monitoring

### Key Metrics to Track

| Metric | View | Alert Threshold | Action |
|--------|------|-----------------|--------|
| **Average Cost/Analysis** | Sessions | > $0.20 | Investigate expensive agents |
| **P95 Latency** | Traces | > 60s | Optimize slow nodes |
| **Quality Score Avg** | Scores | < 6.5 | Review prompts/retrieval |
| **Failed Quality Gates** | Traces (tag) | > 20% | Improve synthesis quality |
| **Retry Rate** | Traces (metadata) | > 10% | Reduce quality gate failures |

### Cost Optimization

**Query most expensive agents:**

```plaintext
DASHBOARD VIEW:
1. Traces → Group by: metadata.agent_type
2. Sort by: total_cost DESC
3. Identify outliers

INTERPRETATION:
- Tech Comparator costs $0.08/trace → Review context size
- Security Auditor costs $0.12/trace → Reduce redundant checks
```

**Check token usage patterns:**

```plaintext
1. Click into expensive trace
2. View generation details
3. Check input_tokens vs output_tokens
4. Optimize prompts to reduce tokens:
   - Compress context (fewer chunks)
   - More concise system prompts
   - Shorter examples
```

---

## Troubleshooting

### Issue 1: No Traces Appearing

**Symptoms:** Dashboard shows 0 traces despite running analyses.

**Diagnosis:**

```bash
# Check Langfuse is running
docker-compose ps langfuse-web
# Should show "Up"

# Check backend logs for errors
docker-compose logs backend | grep -i langfuse
# Look for "Langfuse error" or connection failures

# Verify API keys
curl -u "$LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY" \
  http://localhost:3000/api/public/traces
# Should return JSON, not 401
```

**Solutions:**
1. Restart Langfuse services: `docker-compose restart langfuse-web langfuse-worker`
2. Check `.env` has correct `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`
3. Verify `LANGFUSE_HOST=http://localhost:3000` (not https)

### Issue 2: Missing Scores

**Symptoms:** Traces appear but no quality scores attached.

**Diagnosis:**

```python
# Check if quality gate is running
# In backend logs:
grep "quality_gate_evaluation_complete" logs/app.log

# Should see:
# quality_gate_evaluation_complete
#   relevance_score=0.85
#   depth_score=0.78
#   coherence_score=0.82
```

**Solutions:**
1. Verify G-Eval is configured (Gemini API key in `.env`)
2. Check quality gate isn't being skipped (e.g., no aggregated insights)
3. Look for errors in `quality_gate_node` logs

### Issue 3: Session Grouping Not Working

**Symptoms:** All traces appear as separate sessions instead of grouped.

**Diagnosis:**

```python
# Check session_id is being set
# In backend code:
from app.core.tracing import update_current_trace

update_current_trace(
    session_id=f"analysis-{analysis_id}",  # Must match format
    user_id="anonymous"
)
```

**Solutions:**
1. Verify `session_id` format: `"analysis-<uuid>"`
2. Ensure all traces in workflow use same `session_id`
3. Check Langfuse SDK version (needs v3.0+)

### Issue 4: High Memory Usage

**Symptoms:** Langfuse web container uses >2GB RAM.

**Diagnosis:**

```bash
docker stats langfuse-web
# Check MEM USAGE column
```

**Solutions:**
1. Increase Docker memory limit (Settings → Resources → Memory → 4GB)
2. Reduce trace retention in Langfuse settings (Settings → Retention → 30 days)
3. Archive old traces to external storage

---

## Integration Points

### Backend Integration

**Tracing Decorator:**

```python
# app/core/tracing.py
from langfuse import observe

@observe(name="my_function", as_type="span")
async def my_function(state: AnalysisState):
    # Automatically traced in Langfuse
    return result
```

**Runtime Metadata Updates:**

```python
from app.core.tracing import update_current_trace

update_current_trace(
    session_id=f"analysis-{analysis_id}",
    user_id="anonymous",
    metadata={
        "analysis_id": str(analysis_id),
        "content_type": "article",
        "url": "https://example.com/post"
    },
    tags=["workflow", "production"]
)
```

**Quality Score Submission:**

```python
# app/domains/analysis/workflows/nodes/quality_gate_node.py
from langfuse import get_client

langfuse = get_client()
trace_id = get_current_trace_id()

langfuse.score(
    trace_id=trace_id,
    name="quality_relevance",
    value=relevance_score,  # 0-10
    comment=f"G-Eval score: {relevance_score}/10"
)
```

### Prompt Management Integration

**Fetch Prompt:**

```python
from app.shared.services.prompts.prompt_manager import PromptManager

prompt_manager = PromptManager()
prompt = await prompt_manager.get_prompt(
    name="security_auditor",
    label="production"
)
compiled_prompt = prompt.compile(context=context_data)
```

**3-Level Cache:**
```
LRU (in-memory) → Redis (5 min TTL) → Langfuse (source of truth)
```

---

## Advanced Features

### 1. Human Annotation Queue

**Purpose:** Review low-quality artifacts and provide feedback.

**Setup:**

```bash
# From backend/
poetry run python scripts/setup_langfuse_annotation_queue.py

# Creates:
# - Annotation queue in Langfuse
# - Filters for quality:low traces
# - Annotation UI link
```

**Workflow:**

1. Low-quality artifact tagged `quality:low`
2. Appears in annotation queue automatically
3. Human reviewer:
   - Reads artifact
   - Marks thumbs up/down
   - Adds comments on issues
4. Feedback stored in Langfuse
5. Future: Train on human preferences

### 2. Dataset Evaluation Runs

**Purpose:** Automated regression testing on golden dataset.

**Setup:**

```python
# scripts/run_golden_dataset_evaluation.py
from langfuse import Langfuse

langfuse = Langfuse()
dataset = langfuse.get_dataset("golden_dataset")

for item in dataset.items:
    # Run analysis
    result = await run_analysis(item.input["url"])

    # Create trace linked to dataset item
    langfuse.trace(
        name="golden_eval",
        metadata={"dataset_item_id": item.id}
    ).generation(
        input=item.input,
        output=result.artifact_content,
        usage=result.usage
    )

    # Score accuracy
    accuracy = compare_artifacts(item.expected_output, result.artifact_content)
    langfuse.score(
        trace_id=trace.id,
        name="accuracy",
        value=accuracy
    )
```

**View Results:**
- **Datasets** view → Click "golden_dataset"
- See all runs with accuracy scores
- Compare runs before/after prompt changes

---

## Best Practices

### 1. Consistent Naming Conventions

- **Session IDs:** `analysis-<uuid>` (maps to AnalysisID)
- **User IDs:** `anonymous` (future: actual user IDs when auth is added)
- **Tags:** Use lowercase with hyphens (`quality-gate`, not `Quality_Gate`)
- **Metadata keys:** Use snake_case (`analysis_id`, not `analysisId`)

### 2. Tag Strategy

**Applied automatically:**
- `quality:high`, `quality:medium`, `quality:low` (from quality_avg score)
- `gate:passed`, `gate:failed` (from quality gate result)

**Add manually for filtering:**
- `workflow` - Top-level workflow traces
- `node` - Individual node traces
- `agent` - Agent execution traces
- `production` - Production environment
- `staging` - Staging environment

### 3. Metadata Standards

**Always include:**
- `analysis_id` - Links to database record
- `content_type` - article, tutorial, repository, video
- `url` - Source URL analyzed

**Include when relevant:**
- `retry_count` - Quality gate retry attempts
- `agent_type` - Which agent generated trace
- `chunk_count` - Number of chunks retrieved
- `token_count` - Total tokens used

### 4. Cost Monitoring

- **Daily:** Check total spend in Sessions view
- **Weekly:** Review cost per agent type
- **Monthly:** Set budget alerts (future: Langfuse webhooks)

### 5. Quality Monitoring

- **Real-time:** Monitor `gate:failed` tags
- **Daily:** Check average `quality_avg` score
- **Weekly:** Review `quality:low` traces for patterns

---

## Resources

### Official Documentation

- [Langfuse Docs](https://langfuse.com/docs) - Complete documentation
- [Python SDK](https://langfuse.com/docs/sdk/python) - Python integration guide
- [Tracing Guide](https://langfuse.com/docs/tracing) - Tracing best practices
- [Scoring API](https://langfuse.com/docs/scores/overview) - Quality scoring
- [Prompt Management](https://langfuse.com/docs/prompts) - Prompt versioning
- [Self-Hosting](https://langfuse.com/docs/deployment/self-host) - Deployment guide

### SkillForge Documentation

- [Langfuse Skill](../.claude/skills/langfuse-observability/SKILL.md) - Technical integration details
- [Langfuse MCP Integration](./LANGFUSE_MCP_INTEGRATION.md) - Prompt management via Claude Code
- [Langfuse MCP Quickstart](./LANGFUSE_MCP_QUICKSTART.md) - 5-minute setup guide
- [Migration Guide](./LANGSMITH_TO_LANGFUSE_MIGRATION.md) - LangSmith → Langfuse migration
- [Integration Gaps](./LANGFUSE_INTEGRATION_GAPS.md) - Feature status and roadmap

### Backend Code References

- `backend/app/core/tracing.py` - Tracing utilities (`@observe`, `update_current_trace`)
- `backend/app/domains/analysis/workflows/nodes/quality_gate_node.py` - Quality scoring
- `backend/app/shared/services/prompts/prompt_manager.py` - Prompt management with caching
- `backend/app/main.py:120-130` - Langfuse client initialization

---

## FAQ

### Q: Can I use Langfuse Cloud instead of self-hosted?

**A:** Yes, but not recommended for SkillForge. Self-hosted provides:
- Complete data control (no PII leaving infrastructure)
- No usage limits (cloud has trace limits on free tier)
- No costs (cloud charges for high volume)

To use cloud: Set `LANGFUSE_HOST=https://cloud.langfuse.com` and get API keys from cloud dashboard.

### Q: How long are traces retained?

**A:** Default: 90 days. Configure in Langfuse UI:
1. Settings → Data Retention
2. Set retention period (30/60/90/180 days)
3. Older traces auto-deleted

### Q: Can I export traces for offline analysis?

**A:** Yes, via API:

```python
from langfuse import Langfuse
langfuse = Langfuse()

# Export last 7 days
traces = langfuse.fetch_traces(
    from_timestamp=datetime.now() - timedelta(days=7),
    to_timestamp=datetime.now()
)

# Save to JSON
import json
with open("traces.json", "w") as f:
    json.dump([t.dict() for t in traces], f)
```

### Q: How do I set up alerts for quality issues?

**A:** Future enhancement. Planned approach:
1. Use Langfuse webhooks (on score created)
2. Trigger Lambda/Cloud Function
3. Check if `quality_avg < 5.0`
4. Send Slack notification

### Q: Can I integrate Langfuse with Grafana?

**A:** Yes, Langfuse exposes metrics via:
- PostgreSQL database (direct queries)
- REST API (custom Grafana datasource)
- Prometheus exporter (community plugin)

Example Grafana dashboard: Track P95 latency, cost trends, quality scores over time.

### Q: What happens if Langfuse is down?

**A:** SkillForge continues to work:
1. Tracing silently fails (no exceptions)
2. Analyses complete normally
3. Traces buffered in memory (lost on restart)
4. Quality gate still runs (scores not recorded)

**Mitigation:** Use Docker health checks and auto-restart policies.

---

## Support

**Issues with Langfuse dashboard?**
1. Check [Troubleshooting](#troubleshooting) section
2. Review [Integration Gaps](./LANGFUSE_INTEGRATION_GAPS.md) for known issues
3. Search Langfuse GitHub issues: https://github.com/langfuse/langfuse/issues
4. Ask in SkillForge Slack #dev-backend channel

**Feature requests?**
- Create issue in SkillForge repo with label `langfuse`
- Tag with priority (P0-P3)
- Include use case and expected behavior
