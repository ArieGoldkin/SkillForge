# 🔄 LangSmith → Langfuse Migration Analysis
**Date:** December 18, 2025
**Status:** Assessment & Planning
**Last Updated:** December 18, 2025 (v2.0 - December 2025 Best Practices)

---

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║          🔍 LANGSMITH USAGE AUDIT & LANGFUSE MIGRATION ROADMAP                ║
║                                                                              ║
║                    SkillForge Codebase Analysis                              ║
║                    Updated for December 2025                                 ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## 📊 Executive Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  DIFFICULTY ASSESSMENT: ⚠️  MODERATE (6/10)                                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Complexity Factors:                                                  │  │
│  │  • 437+ usage points (decorators, get_current_run_tree)             │  │
│  │  • Custom robust_traceable wrapper                                  │  │
│  │  • Generator filtering workaround (can be removed!)                 │  │
│  │  • Evaluation dataset extraction from traces                         │  │
│  │  • Metrics service integration                                       │  │
│  │  • Test suite with 100+ mocked LangSmith calls                      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Estimated Effort: 3-5 days                                                │
│  Risk Level: Medium                                                        │
│  Breaking Changes: Low (API compatible)                                   │
│                                                                             │
│  🆕 DECEMBER 2025 UPDATES:                                                  │
│     • Langfuse v3 uses ClickHouse for OLAP (not just PostgreSQL)          │
│     • Native MCP server at /api/public/mcp (no build required!)           │
│     • Dataset Item Versioning (Dec 15, 2025)                              │
│     • v2 Metrics API with cursor pagination (Dec 16, 2025)                │
│     • SDK v3 uses @observe decorator and get_client() singleton           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗺️ LangSmith Usage Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  📍 USAGE LOCATIONS (1348+ matches found)                                   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │  1. CORE TRACING INFRASTRUCTURE                                     │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ backend/app/core/tracing.py                                │  │  │
│  │     │   • robust_traceable() decorator wrapper                   │  │  │
│  │     │   • Wraps langsmith.traceable                              │  │  │
│  │     │   • Used in 50+ workflow nodes                             │  │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  2. LANGGRAPH NODE INSTRUMENTATION (50+ nodes)                      │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ domains/analysis/workflows/nodes/agents/                  │  │  │
│  │     │   • tech_comparator_node.py                                │  │  │
│  │     │   • security_auditor_node.py                               │  │  │
│  │     │   • performance_analyst_node.py                             │  │  │
│  │     │   • dependency_mapper_node.py                              │  │  │
│  │     │   • trend_validator_node.py                                │  │  │
│  │     │   • integration_feasibility_node.py                         │  │  │
│  │     │   • code_quality_critic_node.py                            │  │  │
│  │     │   • implementation_planner_node.py                         │  │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  3. TUTOR WORKFLOW NODES (8 nodes)                                 │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ domains/tutor/workflows/nodes/                             │  │  │
│  │     │   • ask_socratic.py                                        │  │  │
│  │     │   • assess_readiness.py                                    │  │  │
│  │     │   • conduct_review.py                                      │  │  │
│  │     │   • deliver_lesson.py                                      │  │  │
│  │     │   • final_challenge.py                                     │  │  │
│  │     │   • generate_syllabus.py                                   │  │  │
│  │     │   • guide_reflection.py                                    │  │  │
│  │     │   • rephrase_explain.py                                    │  │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  4. AGENT INVOCATION & STREAMING                                   │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ domains/analysis/workflows/agents/                        │  │  │
│  │     │   • invocation.py (get_current_run_tree)                  │  │  │
│  │     │   • streaming.py (get_current_run_tree)                   │  │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  5. QUALITY GATE NODE                                               │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ domains/analysis/workflows/nodes/quality_gate_node.py     │  │  │
│  │     │   • Uses langsmith.schemas.Example, Run                   │  │  │
│  │     │   • get_current_run_tree() for metadata                   │  │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  6. EVALUATION SYSTEM                                               │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ evaluation/ingestion/langsmith_extractor.py                 │  │  │
│  │     │   • LangSmithExtractor class                               │  │  │
│  │     │   • Extracts traces → evaluation datasets                  │  │  │
│  │     │   • Client() for querying traces                          │  │  │
│  │     │                                                             │  │  │
│  │     │ evaluation/evaluators/                                     │  │  │
│  │     │   • quality.py (uses Run, Example schemas)                 │  │  │
│  │     │   • cost.py (uses Run, Example schemas)                   │  │  │
│  │     │   • correctness.py (uses Run, Example schemas)            │  │  │
│  │     │   • latency.py (uses Run, Example schemas)                 │  │  │
│  │     │                                                             │  │  │
│  │     │ evaluation/llm_benchmark.py                                 │  │  │
│  │     │   • Client() for metrics extraction                       │  │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  7. METRICS SERVICE                                                 │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ services/metrics/langsmith.py                             │  │  │
│  │     │   • LangSmithMetricsService                               │  │  │
│  │     │   • Client() for querying experiment metrics              │  │  │
│  │     │   • get_agent_metrics(), get_workflow_metrics()            │  │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  8. CONFIGURATION & CLIENT SETUP                                    │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ core/langsmith_config.py                                  │  │  │
│  │     │   • get_langsmith_client()                                │  │  │
│  │     │   • Generator filtering workaround                        │  │  │
│  │     │   • hide_inputs/hide_outputs filters                     │  │  │
│  │     │                                                             │  │  │
│  │     │ main.py                                                   │  │  │
│  │     │   • Client() initialization check                         │  │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  9. TEST SUITE (100+ test files)                                   │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ tests/unit/core/test_tracing.py                           │  │  │
│  │     │ tests/unit/services/test_langsmith_metrics.py             │  │
│  │     │ tests/unit/evaluation/test_langsmith_extractor.py        │  │
│  │     │ tests/unit/workflows/nodes/test_quality_gate_node.py      │  │
│  │     │ tests/unit/workflows/agents/test_invocation.py            │  │
│  │     │ tests/conftest.py (LANGSMITH_TRACING=false)               │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🆕 December 2025 Langfuse Features

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  📅 LANGFUSE CHANGELOG - DECEMBER 2025                                       │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Dec 16, 2025 │ v2 Metrics and Observations API (Beta)                     │
│               │ • Cursor-based pagination                                  │
│               │ • Selective field retrieval                                │
│               │ • Optimized data architecture                              │
│                                                                             │
│  Dec 15, 2025 │ Dataset Item Versioning                                    │
│               │ • Track changes over time                                  │
│               │ • Automatic versioning on add/update/delete               │
│                                                                             │
│  Dec 12, 2025 │ OpenAI GPT-5.2 Support                                     │
│               │ • Day-1 cost tracking                                      │
│               │ • LLM playground support                                   │
│                                                                             │
│  Dec 11, 2025 │ Batch Add Observations to Datasets                         │
│               │ • Select multiple observations                             │
│               │ • Flexible field mapping                                   │
│                                                                             │
│  Dec 2, 2025  │ Pricing Tiers for Model Cost Tracking                      │
│               │ • Context-dependent pricing support                         │
│                                                                             │
│  Nov 20, 2025 │ Native MCP Server (MAJOR UPDATE)                           │
│               │ • Built into Langfuse at /api/public/mcp                  │
│               │ • StreamableHttp transport                                 │
│               │ • No build/install required                                │
│               │ • Write capabilities (create/update prompts)              │
│                                                                             │
│  Nov 14, 2025 │ OpenAI GPT-5.1 Support                                     │
│               │ • LLM-as-a-judge evaluations                               │
│               │ • Comprehensive cost tracking                              │
│                                                                             │
│  Nov 5, 2025  │ Langfuse for Agents                                        │
│               │ • Beautiful tool call rendering                            │
│               │ • Agent Evals for performance analysis                     │
│               │ • Perfect for SkillForge's 8 specialized agents!          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Migration Architecture Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  LANGSMITH (Current)                    LANGFUSE v3 (Target - Dec 2025)    │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  ┌─────────────────────┐              ┌─────────────────────┐            │
│  │ @traceable          │              │ @observe            │            │
│  │ (langsmith)         │    ────>     │ (langfuse)          │            │
│  └─────────────────────┘              └─────────────────────┘            │
│           │                                      │                         │
│           │                                      │                         │
│           v                                      v                         │
│  ┌─────────────────────┐              ┌─────────────────────┐            │
│  │ get_current_run_   │              │ langfuse.update_    │            │
│  │ tree()             │    ────>     │ current_trace()     │            │
│  │                    │              │ langfuse.update_    │            │
│  │                    │              │ current_span()      │            │
│  └─────────────────────┘              └─────────────────────┘            │
│           │                                      │                         │
│           │                                      │                         │
│           v                                      v                         │
│  ┌─────────────────────┐              ┌─────────────────────┐            │
│  │ Client()            │              │ get_client()        │            │
│  │ - hide_inputs       │    ────>     │ (singleton)         │            │
│  │ - hide_outputs      │              │ - auto-configured   │            │
│  │                     │              │ - no generator hack │            │
│  └─────────────────────┘              └─────────────────────┘            │
│           │                                      │                         │
│           │                                      │                         │
│           v                                      v                         │
│  ┌─────────────────────┐              ┌─────────────────────┐            │
│  │ schemas.Run        │              │ Native Python dicts │            │
│  │ schemas.Example    │    ────>     │ (Trace, Span)       │            │
│  │ (Pydantic v1)      │              │ (no Pydantic v1)    │            │
│  └─────────────────────┘              └─────────────────────┘            │
│                                                                             │
│  ┌─────────────────────┐              ┌─────────────────────┐            │
│  │ LangChain Callback │              │ CallbackHandler     │            │
│  │ via traceable      │    ────>     │ from langfuse.      │            │
│  │                    │              │ langchain           │            │
│  └─────────────────────┘              └─────────────────────┘            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏠 Self-Hosted Architecture (December 2025 - Langfuse v3)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  🏗️  LANGFUSE v3 SELF-HOSTED ARCHITECTURE                                   │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  ⚠️  CRITICAL: Langfuse v3 requires ClickHouse for analytics!              │
│      PostgreSQL alone is NOT sufficient for production use.                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │              ┌──────────────────┐                                  │  │
│  │              │   User Browser   │                                  │  │
│  │              │   (localhost:3000)│                                  │  │
│  │              └────────┬─────────┘                                  │  │
│  │                       │                                            │  │
│  │                       ▼                                            │  │
│  │              ┌──────────────────┐                                  │  │
│  │              │  langfuse-web    │◄─── UI + REST API                │  │
│  │              │   (Port 3000)    │                                  │  │
│  │              └────────┬─────────┘                                  │  │
│  │                       │                                            │  │
│  │         ┌─────────────┼─────────────┐                              │  │
│  │         │             │             │                              │  │
│  │         ▼             ▼             ▼                              │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐                     │  │
│  │  │ PostgreSQL │ │ClickHouse │ │   Redis    │                     │  │
│  │  │(transact.) │ │  (OLAP)   │ │(queue/cache)│                     │  │
│  │  └────────────┘ └────────────┘ └────────────┘                     │  │
│  │         │             │             │                              │  │
│  │         └─────────────┼─────────────┘                              │  │
│  │                       │                                            │  │
│  │                       ▼                                            │  │
│  │              ┌──────────────────┐                                  │  │
│  │              │ langfuse-worker  │◄─── Async event processing      │  │
│  │              │   (Port 3030)    │                                  │  │
│  │              └────────┬─────────┘                                  │  │
│  │                       │                                            │  │
│  │                       ▼                                            │  │
│  │              ┌──────────────────┐                                  │  │
│  │              │   MinIO (S3)     │◄─── Blob storage for events     │  │
│  │              │   (Port 9000)    │     and multi-modal inputs      │  │
│  │              └──────────────────┘                                  │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  WHY CLICKHOUSE? (December 2025)                                           │
│  ────────────────────────────────────────────────────────────────────────  │
│  "The row-based storage model of PostgreSQL becomes increasingly           │
│  inefficient when dealing with billions of rows of tracing data,          │
│  leading to slow query times and high resource consumption."              │
│                                                                             │
│  Langfuse v3 adoption: 1000+ self-hosted deployments running ClickHouse   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🐳 Docker Compose Configuration (December 2025)

Add the following to your `docker-compose.yml`:

```yaml
# ═══════════════════════════════════════════════════════════════════════════
# LANGFUSE v3 SELF-HOSTED STACK (December 2025)
# ═══════════════════════════════════════════════════════════════════════════
# Reference: https://github.com/langfuse/langfuse/blob/main/docker-compose.yml
#
# Services:
#   - langfuse-web: Main web application (UI + APIs) - Port 3000
#   - langfuse-worker: Async event processing - Port 3030
#   - langfuse-db: PostgreSQL for transactional data
#   - clickhouse: ClickHouse for analytics/traces (REQUIRED for v3)
#   - langfuse-redis: Redis for queue and cache
#   - minio: S3-compatible blob storage
# ═══════════════════════════════════════════════════════════════════════════

services:
  # ─────────────────────────────────────────────────────────────────────────
  # LANGFUSE WEB - Main Application
  # ─────────────────────────────────────────────────────────────────────────
  langfuse-web:
    image: langfuse/langfuse:3
    container_name: langfuse-web
    ports:
      - "3000:3000"
    environment:
      # Database connections
      DATABASE_URL: postgresql://langfuse:langfuse-secret@langfuse-db:5432/langfuse
      CLICKHOUSE_URL: http://clickhouse:8123
      CLICKHOUSE_USER: default
      CLICKHOUSE_PASSWORD: clickhouse-secret  # CHANGEME
      REDIS_CONNECTION_STRING: redis://:redis-secret@langfuse-redis:6379

      # S3/MinIO for blob storage
      LANGFUSE_S3_EVENT_UPLOAD_ENABLED: "true"
      LANGFUSE_S3_EVENT_UPLOAD_BUCKET: langfuse
      LANGFUSE_S3_EVENT_UPLOAD_REGION: us-east-1
      LANGFUSE_S3_EVENT_UPLOAD_ACCESS_KEY_ID: minio-access-key  # CHANGEME
      LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY: minio-secret-key  # CHANGEME
      LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT: http://minio:9000
      LANGFUSE_S3_EVENT_UPLOAD_FORCE_PATH_STYLE: "true"

      # Security (CHANGEME - use long random strings!)
      NEXTAUTH_SECRET: your-nextauth-secret-min-32-chars  # CHANGEME
      SALT: your-salt-min-32-chars  # CHANGEME
      ENCRYPTION_KEY: your-encryption-key-exactly-64-hex-chars  # CHANGEME
      NEXTAUTH_URL: http://localhost:3000

      # Optional: Initial setup (remove after first run)
      # LANGFUSE_INIT_ORG_ID: my-org
      # LANGFUSE_INIT_ORG_NAME: My Organization
      # LANGFUSE_INIT_PROJECT_ID: skillforge
      # LANGFUSE_INIT_PROJECT_NAME: SkillForge
      # LANGFUSE_INIT_USER_EMAIL: admin@example.com
      # LANGFUSE_INIT_USER_PASSWORD: changeme123  # CHANGEME
    depends_on:
      langfuse-db:
        condition: service_healthy
      clickhouse:
        condition: service_healthy
      langfuse-redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/public/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - skillforge-network

  # ─────────────────────────────────────────────────────────────────────────
  # LANGFUSE WORKER - Async Event Processing
  # ─────────────────────────────────────────────────────────────────────────
  langfuse-worker:
    image: langfuse/langfuse:3
    container_name: langfuse-worker
    command: ["node", "packages/worker/dist/index.js"]
    ports:
      - "3030:3030"
    environment:
      # Same database connections as langfuse-web
      DATABASE_URL: postgresql://langfuse:langfuse-secret@langfuse-db:5432/langfuse
      CLICKHOUSE_URL: http://clickhouse:8123
      CLICKHOUSE_USER: default
      CLICKHOUSE_PASSWORD: clickhouse-secret  # CHANGEME
      REDIS_CONNECTION_STRING: redis://:redis-secret@langfuse-redis:6379

      # S3/MinIO
      LANGFUSE_S3_EVENT_UPLOAD_ENABLED: "true"
      LANGFUSE_S3_EVENT_UPLOAD_BUCKET: langfuse
      LANGFUSE_S3_EVENT_UPLOAD_REGION: us-east-1
      LANGFUSE_S3_EVENT_UPLOAD_ACCESS_KEY_ID: minio-access-key  # CHANGEME
      LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY: minio-secret-key  # CHANGEME
      LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT: http://minio:9000
      LANGFUSE_S3_EVENT_UPLOAD_FORCE_PATH_STYLE: "true"

      # Security
      NEXTAUTH_SECRET: your-nextauth-secret-min-32-chars  # CHANGEME
      SALT: your-salt-min-32-chars  # CHANGEME
      ENCRYPTION_KEY: your-encryption-key-exactly-64-hex-chars  # CHANGEME
    depends_on:
      langfuse-web:
        condition: service_healthy
    networks:
      - skillforge-network

  # ─────────────────────────────────────────────────────────────────────────
  # LANGFUSE DATABASE - PostgreSQL (Transactional Data)
  # ─────────────────────────────────────────────────────────────────────────
  langfuse-db:
    image: postgres:16-alpine
    container_name: langfuse-db
    environment:
      POSTGRES_DB: langfuse
      POSTGRES_USER: langfuse
      POSTGRES_PASSWORD: langfuse-secret  # CHANGEME
    volumes:
      - langfuse_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U langfuse -d langfuse"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - skillforge-network

  # ─────────────────────────────────────────────────────────────────────────
  # CLICKHOUSE - Analytics & Trace Storage (REQUIRED for v3!)
  # ─────────────────────────────────────────────────────────────────────────
  clickhouse:
    image: clickhouse/clickhouse-server:24.8-alpine
    container_name: langfuse-clickhouse
    environment:
      CLICKHOUSE_DB: langfuse
      CLICKHOUSE_USER: default
      CLICKHOUSE_PASSWORD: clickhouse-secret  # CHANGEME
    volumes:
      - langfuse_clickhouse_data:/var/lib/clickhouse
      - langfuse_clickhouse_logs:/var/log/clickhouse-server
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8123/ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - skillforge-network

  # ─────────────────────────────────────────────────────────────────────────
  # REDIS - Queue and Cache
  # ─────────────────────────────────────────────────────────────────────────
  langfuse-redis:
    image: redis:7-alpine
    container_name: langfuse-redis
    command: redis-server --requirepass redis-secret  # CHANGEME
    volumes:
      - langfuse_redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "redis-secret", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - skillforge-network

  # ─────────────────────────────────────────────────────────────────────────
  # MINIO - S3-Compatible Blob Storage
  # ─────────────────────────────────────────────────────────────────────────
  minio:
    image: minio/minio:latest
    container_name: langfuse-minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"   # S3 API
      - "9001:9001"   # Console
    environment:
      MINIO_ROOT_USER: minio-access-key  # CHANGEME
      MINIO_ROOT_PASSWORD: minio-secret-key  # CHANGEME (min 8 chars)
    volumes:
      - langfuse_minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - skillforge-network

  # ─────────────────────────────────────────────────────────────────────────
  # MINIO SETUP - Create bucket on first run
  # ─────────────────────────────────────────────────────────────────────────
  minio-setup:
    image: minio/mc:latest
    container_name: langfuse-minio-setup
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
      mc alias set minio http://minio:9000 minio-access-key minio-secret-key;
      mc mb minio/langfuse --ignore-existing;
      exit 0;
      "
    networks:
      - skillforge-network

# ═══════════════════════════════════════════════════════════════════════════
# VOLUMES
# ═══════════════════════════════════════════════════════════════════════════
volumes:
  langfuse_postgres_data:
  langfuse_clickhouse_data:
  langfuse_clickhouse_logs:
  langfuse_redis_data:
  langfuse_minio_data:

# ═══════════════════════════════════════════════════════════════════════════
# NETWORKS
# ═══════════════════════════════════════════════════════════════════════════
networks:
  skillforge-network:
    driver: bridge
```

### Quick Start Commands

```bash
# Start Langfuse stack
docker-compose up -d langfuse-web langfuse-worker langfuse-db clickhouse langfuse-redis minio minio-setup

# Check status
docker-compose ps

# View logs
docker-compose logs -f langfuse-web langfuse-worker

# Verify health
curl http://localhost:3000/api/public/health

# Access UI
open http://localhost:3000
```

---

## 📋 Detailed Migration Plan

### Phase 1: Core Infrastructure (Day 1)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  STEP 1.1: Replace robust_traceable Decorator                             │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  File: backend/app/core/tracing.py                                         │
│                                                                             │
│  BEFORE (LangSmith):                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langsmith import traceable                                    │  │
│  │                                                                     │  │
│  │ def robust_traceable(...):                                         │  │
│  │     traced_func = traceable(                                       │  │
│  │         run_type=run_type,                                         │  │
│  │         name=name or func.__name__,                                │  │
│  │         tags=tags or [],                                           │  │
│  │         metadata=metadata or {},                                   │  │
│  │     )                                                               │  │
│  │     return traced_func(func)                                        │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  AFTER (Langfuse v3 - December 2025):                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langfuse import observe                                       │  │
│  │                                                                     │  │
│  │ # Type mapping for run_type → as_type                              │  │
│  │ RUN_TYPE_MAP = {                                                    │  │
│  │     "chain": "span",        # Default span type                    │  │
│  │     "tool": "span",         # Tool calls                           │  │
│  │     "llm": "generation",    # LLM calls                            │  │
│  │     "retriever": "span",    # Retrieval operations                 │  │
│  │     "embedding": "span",    # Embedding operations                 │  │
│  │ }                                                                   │  │
│  │                                                                     │  │
│  │ def robust_traceable(                                               │  │
│  │     name: str | None = None,                                        │  │
│  │     run_type: str = "chain",                                        │  │
│  │     tags: list[str] | None = None,                                  │  │
│  │     metadata: dict | None = None,                                   │  │
│  │     **kwargs,                                                       │  │
│  │ ) -> Callable:                                                      │  │
│  │     """Wrapper for Langfuse @observe decorator."""                  │  │
│  │     def decorator(func):                                            │  │
│  │         as_type = RUN_TYPE_MAP.get(run_type, "span")                │  │
│  │         return observe(                                             │  │
│  │             name=name or func.__name__,                             │  │
│  │             as_type=as_type,                                       │  │
│  │             # Note: tags and metadata set via update_current_trace │  │
│  │             **kwargs,                                               │  │
│  │         )(func)                                                     │  │
│  │     return decorator                                                │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ⚠️  KEY CHANGES:                                                          │
│     • run_type="llm" → as_type="generation"                                │
│     • @observe doesn't take tags/metadata directly                        │
│     • Use langfuse.update_current_trace() for runtime metadata            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  STEP 1.2: Replace get_current_run_tree() Calls                            │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  BEFORE (LangSmith):                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langsmith import get_current_run_tree                          │  │
│  │                                                                     │  │
│  │ run_tree = get_current_run_tree()                                   │  │
│  │ if run_tree:                                                        │  │
│  │     run_tree.metadata["analysis_id"] = str(analysis_id)            │  │
│  │     run_tree.tags.append("parallel-execution")                      │  │
│  │     trace_id = str(run_tree.trace_id)                              │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  AFTER (Langfuse v3 - December 2025):                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langfuse import get_client                                     │  │
│  │                                                                     │  │
│  │ langfuse = get_client()  # Singleton - safe to call anywhere       │  │
│  │ if langfuse:                                                        │  │
│  │     # Update trace-level metadata                                  │  │
│  │     langfuse.update_current_trace(                                  │  │
│  │         metadata={"analysis_id": str(analysis_id)},                │  │
│  │         tags=["parallel-execution"],                                │  │
│  │     )                                                               │  │
│  │                                                                     │  │
│  │     # Get trace ID (different API)                                 │  │
│  │     current_trace = langfuse.get_current_trace()                   │  │
│  │     trace_id = current_trace.id if current_trace else None         │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ⚠️  CHANGES:                                                               │
│     • get_client() returns singleton (no need to pass around)             │
│     • Separate trace vs span updates                                     │
│     • Tags are replaced, not appended (pass full list)                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  STEP 1.3: Replace Client Configuration                                    │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  File: backend/app/core/langsmith_config.py → langfuse_config.py          │
│                                                                             │
│  BEFORE (LangSmith):                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langsmith import Client                                        │  │
│  │                                                                     │  │
│  │ # Complex generator filtering workaround                           │  │
│  │ def hide_inputs_with_generator_filter(inputs):                     │  │
│  │     return {k: v if not inspect.isgenerator(v)                    │  │
│  │             else "<generator_filtered>" for k, v in inputs.items()}│  │
│  │                                                                     │  │
│  │ _langsmith_client = Client(                                         │  │
│  │     hide_inputs=hide_inputs_with_generator_filter,                 │  │
│  │     hide_outputs=hide_outputs_with_generator_filter,                │  │
│  │ )                                                                   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  AFTER (Langfuse v3 - December 2025):                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langfuse import Langfuse, get_client                          │  │
│  │ import os                                                          │  │
│  │                                                                     │  │
│  │ def configure_langfuse():                                           │  │
│  │     """Configure Langfuse client.                                   │  │
│  │                                                                     │  │
│  │     Note: Langfuse handles generators automatically - no workaround│  │
│  │     needed! The hide_inputs/hide_outputs code can be deleted.      │  │
│  │     """                                                             │  │
│  │     # Client auto-configures from environment variables            │  │
│  │     # LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL │  │
│  │     client = get_client()                                          │  │
│  │                                                                     │  │
│  │     # Optional: manual configuration                                │  │
│  │     # client = Langfuse(                                           │  │
│  │     #     public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),            │  │
│  │     #     secret_key=os.getenv("LANGFUSE_SECRET_KEY"),            │  │
│  │     #     host=os.getenv("LANGFUSE_BASE_URL",                     │  │
│  │     #                    "http://langfuse-web:3000"),             │  │
│  │     # )                                                            │  │
│  │                                                                     │  │
│  │     return client                                                   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ✅ IMPROVEMENTS:                                                           │
│     • No need for generator filtering workaround (DELETE THAT CODE!)      │
│     • Automatic configuration from environment variables                  │
│     • Singleton pattern via get_client()                                  │
│     • Better environment/release tracking                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 2: LangChain/LangGraph Integration (Day 1-2)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  STEP 2.1: Update LangGraph Workflow Tracing                               │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  BEFORE (LangSmith - automatic via env vars):                              │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ # Just set environment variables:                                   │  │
│  │ # LANGCHAIN_TRACING_V2=true                                        │  │
│  │ # LANGCHAIN_API_KEY=...                                            │  │
│  │                                                                     │  │
│  │ # LangGraph auto-traces via langsmith                              │  │
│  │ result = await graph.ainvoke(state, config)                        │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  AFTER (Langfuse v3 - December 2025):                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langfuse import get_client                                     │  │
│  │ from langfuse.langchain import CallbackHandler                      │  │
│  │                                                                     │  │
│  │ # Create callback handler                                          │  │
│  │ langfuse = get_client()                                            │  │
│  │ langfuse_handler = CallbackHandler()                                │  │
│  │                                                                     │  │
│  │ # Pass callback to LangGraph invocation                            │  │
│  │ result = await graph.ainvoke(                                       │  │
│  │     state,                                                          │  │
│  │     config={                                                        │  │
│  │         "callbacks": [langfuse_handler],                           │  │
│  │         # Optional: propagate session/user context                 │  │
│  │         "configurable": {                                          │  │
│  │             "session_id": session_id,                              │  │
│  │             "user_id": user_id,                                    │  │
│  │         },                                                         │  │
│  │     },                                                              │  │
│  │ )                                                                   │  │
│  │                                                                     │  │
│  │ # IMPORTANT: Flush before exit in serverless/short-lived apps      │  │
│  │ langfuse.flush()                                                   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  📍 FILES TO UPDATE:                                                       │
│     • backend/app/api/v1/workflow_runner.py                               │
│     • backend/app/domains/analysis/workflows/graph.py                     │
│     • backend/app/domains/tutor/workflows/graph.py                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 3: Evaluation System (Day 2)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  STEP 3.1: Replace LangSmithExtractor                                      │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  File: backend/app/evaluation/ingestion/langsmith_extractor.py            │
│  → langfuse_extractor.py                                                  │
│                                                                             │
│  BEFORE (LangSmith):                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langsmith import Client                                        │  │
│  │                                                                     │  │
│  │ client = Client()                                                   │  │
│  │ runs = client.list_runs(                                             │  │
│  │     project_name=config.project_name,                               │  │
│  │     start_time=config.date_start,                                   │  │
│  │     end_time=config.date_end,                                       │  │
│  │     filter=f"eq(tags, '{config.agent_type}')",                      │  │
│  │ )                                                                   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  AFTER (Langfuse v3 - December 2025):                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langfuse import get_client                                     │  │
│  │                                                                     │  │
│  │ langfuse = get_client()                                            │  │
│  │                                                                     │  │
│  │ # Use get_traces() with cursor-based pagination (Dec 2025 v2 API)  │  │
│  │ traces = langfuse.get_traces(                                       │  │
│  │     name=config.agent_type,  # Filter by trace name                │  │
│  │     tags=[config.agent_type],                                       │  │
│  │     from_timestamp=config.date_start,                               │  │
│  │     to_timestamp=config.date_end,                                    │  │
│  │     limit=100,                                                      │  │
│  │ )                                                                   │  │
│  │                                                                     │  │
│  │ # Iterate with cursor-based pagination                              │  │
│  │ all_traces = []                                                     │  │
│  │ while True:                                                         │  │
│  │     all_traces.extend(traces.data)                                 │  │
│  │     if not traces.meta.has_next:                                   │  │
│  │         break                                                       │  │
│  │     traces = langfuse.get_traces(                                   │  │
│  │         cursor=traces.meta.next_cursor,                            │  │
│  │         # ... same filters                                         │  │
│  │     )                                                               │  │
│  │                                                                     │  │
│  │ # Convert traces to evaluation examples                             │  │
│  │ for trace in all_traces:                                            │  │
│  │     example = convert_trace_to_example(trace)                       │  │
│  │     # trace.input, trace.output, trace.metadata, trace.tags         │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ⚠️  API DIFFERENCES:                                                       │
│     • Different query syntax (get_traces vs list_runs)                    │
│     • Cursor-based pagination (v2 Metrics API - Dec 2025)                 │
│     • Trace structure differs from Run structure                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  STEP 3.2: Update Dataset Management (Dec 2025 Versioning!)                │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  NEW FEATURE: Dataset Item Versioning (December 15, 2025)                  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langfuse import get_client                                     │  │
│  │                                                                     │  │
│  │ langfuse = get_client()                                            │  │
│  │                                                                     │  │
│  │ # Create dataset for evaluation                                     │  │
│  │ langfuse.create_dataset(                                            │  │
│  │     name="skillforge-golden-dataset",                               │  │
│  │     description="Golden dataset for SkillForge evaluation",        │  │
│  │     metadata={"version": "2.0", "created_by": "evaluation-pipeline"}│  │
│  │ )                                                                   │  │
│  │                                                                     │  │
│  │ # Add items - AUTOMATICALLY VERSIONED! (Dec 2025 feature)          │  │
│  │ langfuse.create_dataset_item(                                       │  │
│  │     dataset_name="skillforge-golden-dataset",                       │  │
│  │     input={"url": "https://example.com/article"},                  │  │
│  │     expected_output={                                               │  │
│  │         "title": "Expected Title",                                  │  │
│  │         "summary": "Expected Summary",                              │  │
│  │     },                                                              │  │
│  │     metadata={                                                      │  │
│  │         "agent_type": "tech_comparator",                           │  │
│  │         "difficulty": "intermediate",                               │  │
│  │     },                                                              │  │
│  │ )                                                                   │  │
│  │                                                                     │  │
│  │ # Every add/update/delete creates a new version automatically!     │  │
│  │ # View version history in Langfuse UI:                             │  │
│  │ # Datasets > skillforge-golden-dataset > Items Tab                 │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ✅ BENEFITS FOR SKILLFORGE:                                                │
│     • Track golden dataset evolution over time                            │
│     • Audit trail for dataset changes                                     │
│     • Roll back to previous versions if needed                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 4: Quality Gate & Scoring (Day 2-3)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  STEP 4.1: Update Quality Gate Node                                        │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  File: backend/app/domains/analysis/workflows/nodes/quality_gate_node.py  │
│                                                                             │
│  BEFORE (LangSmith):                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langsmith.schemas import Example, Run                          │  │
│  │ from langsmith import get_current_run_tree                          │  │
│  │                                                                     │  │
│  │ run_tree = get_current_run_tree()                                   │  │
│  │ if run_tree:                                                        │  │
│  │     example = Example(                                               │  │
│  │         inputs={"content": content},                                │  │
│  │         outputs={"artifact": artifact},                              │  │
│  │     )                                                               │  │
│  │     run = Run(                                                       │  │
│  │         inputs={"content": content},                                 │  │
│  │         outputs={"artifact": artifact},                             │  │
│  │         start_time=datetime.now(UTC),                                  │  │
│  │         trace_id=uuid4(),                                            │  │
│  │     )                                                               │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  AFTER (Langfuse v3 - December 2025):                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langfuse import get_client                                     │  │
│  │                                                                     │  │
│  │ langfuse = get_client()                                            │  │
│  │                                                                     │  │
│  │ # Score the current trace                                           │  │
│  │ langfuse.score(                                                     │  │
│  │     name="quality_score",                                           │  │
│  │     value=quality_score,  # 0.0 - 1.0                               │  │
│  │     data_type="NUMERIC",                                            │  │
│  │     comment=f"Quality gate: {quality_assessment}",                  │  │
│  │ )                                                                   │  │
│  │                                                                     │  │
│  │ # Add more scores                                                   │  │
│  │ langfuse.score(                                                     │  │
│  │     name="completeness",                                            │  │
│  │     value=completeness_score,                                       │  │
│  │     data_type="NUMERIC",                                            │  │
│  │ )                                                                   │  │
│  │                                                                     │  │
│  │ langfuse.score(                                                     │  │
│  │     name="passed_quality_gate",                                     │  │
│  │     value=passed,  # True/False                                    │  │
│  │     data_type="BOOLEAN",                                            │  │
│  │ )                                                                   │  │
│  │                                                                     │  │
│  │ # Optionally add to dataset for future evaluation                  │  │
│  │ if quality_score >= 0.85:  # High quality examples                  │  │
│  │     langfuse.create_dataset_item(                                   │  │
│  │         dataset_name="quality-gate-passed",                         │  │
│  │         input={"content": content},                                 │  │
│  │         expected_output={"artifact": artifact},                     │  │
│  │         metadata={"quality_score": quality_score},                  │  │
│  │     )                                                               │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ⚠️  CHANGES:                                                               │
│     • No need to create Run/Example objects manually                       │
│     • Use score() API for evaluation metrics                              │
│     • Three data types: NUMERIC, BOOLEAN, CATEGORICAL                     │
│     • Can link scores to dataset items for experiments                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 5: Test Suite Updates (Day 3-4)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  STEP 5.1: Update Test Mocks                                               │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Files to Update:                                                          │
│    • tests/unit/core/test_tracing.py                                      │
│    • tests/unit/services/test_langsmith_metrics.py                         │
│    • tests/unit/evaluation/test_langsmith_extractor.py                    │
│    • tests/unit/workflows/nodes/test_quality_gate_node.py                 │
│    • tests/unit/workflows/agents/test_invocation.py                        │
│    • tests/conftest.py                                                    │
│                                                                             │
│  BEFORE (LangSmith):                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ @patch("langsmith.get_current_run_tree")                            │  │
│  │ @patch("langsmith.schemas.Run")                                      │  │
│  │ @patch("langsmith.schemas.Example")                                  │  │
│  │ def test_something(mock_run_tree, mock_run, mock_example):          │  │
│  │     mock_run_tree.return_value = Mock(                               │  │
│  │         trace_id=uuid4(),                                           │  │
│  │         metadata={},                                                 │  │
│  │         tags=[],                                                    │  │
│  │     )                                                               │  │
│  │     # Test code                                                      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  AFTER (Langfuse v3 - December 2025):                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ @patch("langfuse.get_client")                                       │  │
│  │ def test_something(mock_get_client):                                 │  │
│  │     mock_langfuse = Mock()                                          │  │
│  │     mock_get_client.return_value = mock_langfuse                    │  │
│  │                                                                     │  │
│  │     # Mock trace retrieval                                          │  │
│  │     mock_langfuse.get_current_trace.return_value = Mock(            │  │
│  │         id="trace-123",                                             │  │
│  │         metadata={},                                                 │  │
│  │         tags=[],                                                    │  │
│  │     )                                                               │  │
│  │                                                                     │  │
│  │     # Test code                                                      │  │
│  │                                                                     │  │
│  │     # Verify Langfuse calls                                         │  │
│  │     mock_langfuse.update_current_trace.assert_called_with(          │  │
│  │         metadata={"analysis_id": "..."},                            │  │
│  │     )                                                               │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ⚠️  CHANGES:                                                               │
│     • Update all @patch decorators from langsmith → langfuse              │
│     • Update mock return values to match Langfuse API                     │
│     • Update conftest.py to disable Langfuse tracing                      │
│                                                                             │
│  CONFTEST.PY UPDATE:                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ import os                                                          │  │
│  │                                                                     │  │
│  │ # Disable Langfuse tracing in tests                                │  │
│  │ os.environ["LANGFUSE_ENABLED"] = "false"                           │  │
│  │ os.environ.pop("LANGFUSE_PUBLIC_KEY", None)                        │  │
│  │ os.environ.pop("LANGFUSE_SECRET_KEY", None)                        │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔌 MCP Server Configuration (December 2025 - UPDATED!)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  🆕 NATIVE MCP SERVER (November 20, 2025)                                   │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  ⚠️  MAJOR UPDATE: Langfuse now has a NATIVE MCP server built-in!          │
│     No need to clone/build the mcp-server-langfuse repo anymore.          │
│     The native server uses StreamableHttp and includes write operations.  │
│                                                                             │
│  ENDPOINT: /api/public/mcp (StreamableHttp transport)                      │
│                                                                             │
│  AVAILABLE MCP TOOLS:                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │  READ OPERATIONS:                                                   │  │
│  │    • getPrompt - Retrieve and compile a specific prompt            │  │
│  │    • listPrompts - List all available prompts (with pagination)     │  │
│  │                                                                     │  │
│  │  WRITE OPERATIONS (NEW in Nov 2025!):                               │  │
│  │    • createTextPrompt - Create a new text prompt version           │  │
│  │    • createChatPrompt - Create a new chat prompt version           │  │
│  │    • updatePromptLabels - Manage labels across versions            │  │
│  │                                                                     │  │
│  │  Note: Only prompts marked with "production" label are returned     │  │
│  │  by default. Configure allowlist for read-only access if needed.   │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### MCP Server Setup for Different Clients

#### Claude Code (CLI) - Recommended

```bash
# One-liner setup!
claude mcp add \
  --transport http \
  langfuse \
  http://localhost:3000/api/public/mcp \
  --header "Authorization: Basic $(echo -n 'pk-lf-...:sk-lf-...' | base64)"
```

Or add to `.mcp.json`:

```json
{
  "mcpServers": {
    "langfuse": {
      "transport": "http",
      "url": "http://localhost:3000/api/public/mcp",
      "headers": {
        "Authorization": "Basic <base64-encoded-pk:sk>"
      }
    }
  }
}
```

#### Cursor IDE

Add to Cursor settings (Settings > MCP Servers):

```json
{
  "mcpServers": {
    "langfuse": {
      "command": "npx",
      "args": ["@langfuse/mcp-server"],
      "env": {
        "LANGFUSE_PUBLIC_KEY": "pk-lf-...",
        "LANGFUSE_SECRET_KEY": "sk-lf-...",
        "LANGFUSE_BASEURL": "http://localhost:3000"
      }
    }
  }
}
```

#### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "langfuse": {
      "command": "npx",
      "args": ["@langfuse/mcp-server"],
      "env": {
        "LANGFUSE_PUBLIC_KEY": "pk-lf-...",
        "LANGFUSE_SECRET_KEY": "sk-lf-...",
        "LANGFUSE_BASEURL": "http://localhost:3000"
      }
    }
  }
}
```

#### Alternative: Native HTTP Transport (No npx required)

For clients supporting HTTP transport:

```json
{
  "mcpServers": {
    "langfuse": {
      "transportType": "http",
      "url": "http://localhost:3000/api/public/mcp",
      "headers": {
        "Authorization": "Basic <base64-encoded-pk:sk>"
      }
    }
  }
}
```

---

## 📦 Dependency Changes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  pyproject.toml Updates                                                     │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  ADD:                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ # Langfuse SDK v3 (December 2025)                                   │  │
│  │ langfuse = "^3.0.0"                                                 │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  KEEP (langsmith is transitive via langchain, not explicitly needed):      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ # LangChain still includes langsmith as transitive dependency      │  │
│  │ # but we won't use it directly anymore                              │  │
│  │ langchain = "^1.1.2"                                                │  │
│  │ langgraph = "^1.0.4"                                                │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ENVIRONMENT VARIABLES (Self-Hosted):                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ # REMOVE (LangSmith)                                                │  │
│  │ # LANGCHAIN_TRACING_V2=true                                        │  │
│  │ # LANGSMITH_API_KEY=...                                            │  │
│  │ # LANGCHAIN_API_KEY=...                                            │  │
│  │                                                                     │  │
│  │ # ADD (Langfuse - Self-Hosted)                                      │  │
│  │ LANGFUSE_PUBLIC_KEY=pk-lf-...    # From Langfuse UI                │  │
│  │ LANGFUSE_SECRET_KEY=sk-lf-...    # From Langfuse UI                │  │
│  │ LANGFUSE_BASE_URL=http://langfuse-web:3000  # Docker internal      │  │
│  │ LANGFUSE_ENABLED=true            # Enable tracing                  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ✅ BENEFITS OF SELF-HOSTED:                                                │
│     • FREE - No per-trace costs (LangSmith charges per trace)             │
│     • Full data control - All traces stored locally                         │
│     • No internet required - Works offline                                  │
│     • Fast - No network latency to cloud                                   │
│     • Privacy - Data never leaves your infrastructure                       │
│     • Native MCP - Prompt management via MCP                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Migration Checklist (December 2025)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE 0: INFRASTRUCTURE (NEW - Dec 2025 Architecture)                     │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Add Langfuse v3 services to docker-compose.yml                        │
│      [ ] langfuse-web (port 3000)                                         │
│      [ ] langfuse-worker (port 3030)                                      │
│      [ ] langfuse-db (PostgreSQL)                                         │
│      [ ] clickhouse (REQUIRED for v3!)                                    │
│      [ ] langfuse-redis                                                   │
│      [ ] minio (S3-compatible storage)                                    │
│  [ ] Generate secure secrets (NEXTAUTH_SECRET, SALT, ENCRYPTION_KEY)      │
│  [ ] Start Langfuse stack: docker-compose up -d langfuse-web ...         │
│  [ ] Access UI: http://localhost:3000                                     │
│  [ ] Create admin account (first user = admin)                            │
│  [ ] Create project "skillforge"                                          │
│  [ ] Generate API keys (Settings → API Keys)                               │
│                                                                             │
│  PHASE 1: DEPENDENCIES                                                     │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Add langfuse = "^3.0.0" to pyproject.toml                            │
│  [ ] Run: poetry lock && poetry install                                   │
│  [ ] Update backend/.env with Langfuse credentials                        │
│  [ ] Create feature branch: issue/XXX-langfuse-migration                   │
│                                                                             │
│  PHASE 2: CORE INFRASTRUCTURE                                              │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Create langfuse_config.py (copy structure from langsmith_config.py)  │
│  [ ] Update robust_traceable decorator (tracing.py)                       │
│  [ ] Replace get_current_run_tree() → get_client() pattern               │
│  [ ] DELETE generator filtering code (not needed!)                        │
│  [ ] Update main.py startup initialization                                │
│                                                                             │
│  PHASE 3: LANGCHAIN/LANGGRAPH INTEGRATION                                  │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Import CallbackHandler from langfuse.langchain                       │
│  [ ] Update workflow_runner.py to pass callbacks                          │
│  [ ] Update analysis workflow graph.py                                    │
│  [ ] Update tutor workflow graph.py                                       │
│  [ ] Add langfuse.flush() for serverless environments                     │
│                                                                             │
│  PHASE 4: WORKFLOW NODES (50+ files)                                       │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Update 8 agent nodes (tech_comparator, security_auditor, etc.)       │
│  [ ] Update 8 tutor nodes                                                  │
│  [ ] Update quality_gate_node.py (scoring API)                            │
│  [ ] Update agent invocation/streaming                                     │
│                                                                             │
│  PHASE 5: EVALUATION SYSTEM                                                │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Create langfuse_extractor.py (replace langsmith_extractor.py)        │
│  [ ] Update evaluator schemas (quality, cost, correctness, latency)       │
│  [ ] Update llm_benchmark.py                                               │
│  [ ] Migrate golden dataset to Langfuse datasets                          │
│  [ ] Enable dataset item versioning (Dec 2025 feature)                    │
│                                                                             │
│  PHASE 6: METRICS SERVICE                                                  │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Create langfuse_metrics.py (replace langsmith.py)                    │
│  [ ] Update metrics aggregation logic                                       │
│  [ ] Use v2 Metrics API with cursor pagination (Dec 2025)                 │
│                                                                             │
│  PHASE 7: TEST SUITE (100+ files)                                          │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Update test mocks (@patch decorators)                                │
│  [ ] Update conftest.py (disable Langfuse tracing)                        │
│  [ ] Run full test suite                                                   │
│  [ ] Verify coverage ≥80%                                                 │
│                                                                             │
│  PHASE 8: VALIDATION                                                       │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Run integration tests                                                │
│  [ ] Verify traces appear in Langfuse UI                                   │
│  [ ] Test all 8 agent traces render with tool calls (Nov 2025 feature)   │
│  [ ] Verify metrics aggregation                                            │
│  [ ] Verify evaluation extraction works                                    │
│  [ ] Test MCP prompt access (if configured)                               │
│  [ ] Performance testing (no regressions)                                   │
│                                                                             │
│  PHASE 9: CLEANUP                                                          │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Remove LangSmith environment variables from .env                     │
│  [ ] Delete langsmith_config.py                                           │
│  [ ] Delete langsmith_extractor.py                                        │
│  [ ] Delete langsmith.py (metrics service)                                │
│  [ ] Update documentation                                                  │
│  [ ] Create PR to dev                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Differences Summary (December 2025)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  🔴 CRITICAL DIFFERENCES                                                    │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  1. DECORATOR API                                                          │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ LangSmith: @traceable(run_type="llm")                          │  │
│     │ Langfuse:  @observe(as_type="generation")                      │  │
│     │                                                                │  │
│     │ Mapping: llm → generation, chain → span, tool → span          │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  2. CLIENT ACCESS                                                          │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ LangSmith: Client() or get_current_run_tree()                  │  │
│     │ Langfuse:  get_client() singleton                              │  │
│     │                                                                │  │
│     │ Key: Langfuse uses singleton pattern - call get_client()       │  │
│     │      anywhere, no need to pass client around                   │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  3. METADATA UPDATES                                                       │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ LangSmith: run_tree.metadata["key"] = value                    │  │
│     │ Langfuse:  langfuse.update_current_trace(metadata={...})       │  │
│     │                                                                │  │
│     │ Key: Method call vs direct assignment                          │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  4. TRACE QUERYING (v2 API - Dec 2025)                                     │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ LangSmith: client.list_runs(filter="eq(tags, 'x')")             │  │
│     │ Langfuse:  langfuse.get_traces(tags=["x"])                     │  │
│     │                                                                │  │
│     │ Key: Cursor-based pagination, selective field retrieval        │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  5. GENERATOR FILTERING                                                    │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ LangSmith: Required hide_inputs/hide_outputs workaround        │  │
│     │ Langfuse:  Handles generators automatically                    │  │
│     │                                                                │  │
│     │ ✅ DELETE 50+ lines of generator filtering code!               │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  6. SELF-HOSTING ARCHITECTURE                                              │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ LangSmith: PostgreSQL only (or Enterprise cloud)               │  │
│     │ Langfuse:  PostgreSQL + ClickHouse + Redis + S3 (v3)          │  │
│     │                                                                │  │
│     │ Key: ClickHouse is REQUIRED for v3 - handles analytics at     │  │
│     │      scale (1000+ deployments running it successfully)         │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  7. MCP SUPPORT                                                            │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ LangSmith: Exposes agents as MCP tools                         │  │
│     │ Langfuse:  Native MCP server for prompt management             │  │
│     │            (/api/public/mcp - StreamableHttp)                  │  │
│     │                                                                │  │
│     │ Key: Langfuse MCP = access prompts from Claude/Cursor/etc.     │  │
│     │      No build required - built into Langfuse!                  │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ✅ Benefits of Migration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  🎁 ADVANTAGES OF LANGFUSE (December 2025)                                  │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  ✅ Open Source & Self-Hostable (FREE!)                                    │
│     • No per-trace costs (LangSmith charges per trace)                    │
│     • Full control over data and infrastructure                           │
│     • 1000+ self-hosted deployments in production                          │
│     • Can run on-premises or cloud                                         │
│                                                                             │
│  ✅ Better Generator Handling                                               │
│     • No need for hide_inputs/hide_outputs workaround                     │
│     • Automatic handling of async generators                               │
│     • DELETE 50+ lines of generator filtering code!                        │
│                                                                             │
│  ✅ Agent Tracing (November 2025)                                           │
│     • Beautiful tool call rendering                                        │
│     • Agent Evals for performance analysis                                 │
│     • PERFECT for SkillForge's 8 specialized agents!                      │
│                                                                             │
│  ✅ Dataset Versioning (December 2025)                                      │
│     • Track golden dataset changes over time                              │
│     • Automatic versioning on add/update/delete                            │
│     • Audit trail for dataset evolution                                    │
│                                                                             │
│  ✅ Native MCP Server (November 2025)                                       │
│     • Built into Langfuse at /api/public/mcp                              │
│     • No build/install required                                            │
│     • Read AND write prompts via MCP                                      │
│     • Works with Claude Desktop, Cursor, Claude Code                       │
│                                                                             │
│  ✅ v2 Metrics API (December 2025)                                          │
│     • Cursor-based pagination                                              │
│     • Selective field retrieval                                            │
│     • Optimized for large datasets                                         │
│                                                                             │
│  ✅ Modern Architecture                                                     │
│     • ClickHouse for analytics (fast queries at scale)                    │
│     • Event-driven processing                                              │
│     • Queued trace ingestion                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📚 Best Practices (December 2025)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  🎯 MIGRATION BEST PRACTICES                                                │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  1. INCREMENTAL MIGRATION                                                   │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ • Start with core tracing infrastructure                        │  │
│     │ • Migrate one workflow at a time                                │  │
│     │ • Keep LangSmith running in parallel during transition          │  │
│     │ • Use feature flags to toggle between providers                  │  │
│     │                                                                  │  │
│     │ Example feature flag:                                            │  │
│     │   USE_LANGFUSE = os.getenv("USE_LANGFUSE", "false") == "true"   │  │
│     │   if USE_LANGFUSE:                                              │  │
│     │       from langfuse import observe as traceable                 │  │
│     │   else:                                                          │  │
│     │       from langsmith import traceable                           │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  2. TESTING STRATEGY                                                        │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ • Run both LangSmith and Langfuse in parallel initially        │  │
│     │ • Compare trace outputs for consistency                         │  │
│     │ • Verify all test cases pass                                    │  │
│     │ • Test with real workflows before full migration                │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  3. FLUSH IN SHORT-LIVED APPS                                               │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ # IMPORTANT: Langfuse uses async processing                     │  │
│     │ # Always flush before exit in serverless/CLI/tests              │  │
│     │                                                                 │  │
│     │ langfuse = get_client()                                        │  │
│     │ try:                                                            │  │
│     │     # Your code here                                            │  │
│     │ finally:                                                        │  │
│     │     langfuse.flush()  # Ensure traces are sent!                │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  4. MONITORING DURING MIGRATION                                             │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ • Monitor trace volume in Langfuse UI                          │  │
│     │ • Set up alerts for missing traces                              │  │
│     │ • Track error rates during migration                            │  │
│     │ • Verify cost tracking accuracy                                 │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  5. ROLLBACK PLAN                                                           │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ • Keep LangSmith code in feature branch until stable           │  │
│     │ • Use feature flags for easy rollback                           │  │
│     │ • Document rollback procedure                                    │  │
│     │ • Test rollback process in staging                              │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔗 References

### Official Documentation
- **Langfuse Python SDK v3 Docs:** https://langfuse.com/docs/sdk/python
- **Langfuse Self-Hosting:** https://langfuse.com/self-hosting
- **Langfuse Docker Compose:** https://github.com/langfuse/langfuse/blob/main/docker-compose.yml
- **Langfuse v2 to v3 Upgrade Guide:** https://langfuse.com/self-hosting/upgrade/upgrade-guides/upgrade-v2-to-v3
- **Langfuse Changelog:** https://langfuse.com/changelog

### LangChain/LangGraph Integration
- **LangChain Tracing:** https://langfuse.com/docs/integrations/langchain/tracing
- **@observe Decorator:** https://langfuse.com/docs/sdk/python/decorators

### MCP Integration
- **Native MCP Server (Nov 2025):** https://langfuse.com/changelog/2025-11-20-native-mcp-server
- **MCP Server GitHub:** https://github.com/langfuse/mcp-server-langfuse
- **MCP Prompts Docs:** https://langfuse.com/docs/prompt-management/features/mcp-server

### December 2025 Features
- **Dataset Item Versioning (Dec 15):** https://langfuse.com/changelog
- **v2 Metrics API (Dec 16):** https://langfuse.com/changelog
- **Agent Tracing (Nov 5):** https://langfuse.com/docs/tracing-features/agents

### Comparison
- **Langfuse vs LangSmith:** https://langfuse.com/faq/all/langsmith-alternative
- **LangWatch vs LangSmith vs Langfuse 2025:** https://langwatch.ai/blog/langwatch-vs-langsmith-vs-braintrust-vs-langfuse-choosing-the-best-llm-evaluation-monitoring-tool-in-2025

---

## 📝 Notes

- **Generator Filtering:** Can be removed entirely (Langfuse handles this automatically) - DELETE 50+ lines!
- **Test Coverage:** Ensure ≥80% coverage maintained after migration
- **Breaking Changes:** Minimal - mostly API surface changes
- **Performance:** Should be better (no generator filtering overhead, ClickHouse for analytics)
- **MCP Support:** Native server at /api/public/mcp - no build required!
- **Architecture:** v3 requires ClickHouse - PostgreSQL alone is NOT sufficient

---

**Last Updated:** December 18, 2025 (v2.0 - December 2025 Best Practices)
**Next Steps:** Create feature branch and begin Phase 0 infrastructure setup
