# Backend Debugging Guide

This guide covers multiple approaches to debug the SkillForge backend.

## Table of Contents

1. [VS Code Debugging](#vs-code-debugging)
2. [Docker Container Debugging](#docker-container-debugging)
3. [Enhanced Logging for Debugging](#enhanced-logging-for-debugging)
4. [Langfuse Trace Correlation](#langfuse-trace-correlation)
5. [Langfuse Studio Local Debugging](#langfuse-studio-local-debugging)
6. [Common Debugging Scenarios](#common-debugging-scenarios)

---

## VS Code Debugging

### Option 1: Local Debugging (Recommended for Development)

**Prerequisites:**
- Python 3.13 installed locally
- Backend dependencies installed (`poetry install` in `backend/` directory)
- Database accessible (either local PostgreSQL or Docker postgres running)

**Steps:**

1. **Start PostgreSQL** (if using Docker):
   ```bash
   docker-compose up -d postgres
   ```

2. **Set up environment variables**:
   - Copy `backend/.env.example` to `backend/.env`
   - Fill in required values (API keys, database URL, etc.)

3. **Start debugging**:
   - Open VS Code
   - Go to Run and Debug (F5 or Cmd+Shift+D)
   - Select "Python: FastAPI (Local)" from the dropdown
   - Press F5 or click the green play button
   - Set breakpoints in your code
   - The debugger will stop at breakpoints

**Benefits:**
- Fast iteration (no Docker rebuild needed)
- Full debugging features (breakpoints, variable inspection, call stack)
- Direct access to local files

### Option 2: Docker Attach Debugging

**Prerequisites:**
- Backend container running with debugpy installed
- Port 5678 exposed from container

**Steps:**

1. **Modify docker-compose.yml** to add debugpy and expose port:
   ```yaml
   backend:
     ports:
       - "8500:8500"
       - "5678:5678"  # Debug port
     command: >
       sh -c "
         pip install debugpy &&
         python -m debugpy --listen 0.0.0.0:5678 -m uvicorn app.main:app --host 0.0.0.0 --port 8500 --reload
       "
   ```

2. **Start the backend container**:
   ```bash
   docker-compose up backend
   ```

3. **Attach debugger**:
   - In VS Code, select "Python: FastAPI (Docker - Attach)"
   - Press F5
   - Set breakpoints
   - The debugger will attach to the running container

**Note:** This requires modifying the Docker setup. For production-like debugging, use Option 1 or the logging approach below.

---

## Docker Container Debugging

### Viewing Logs

**Real-time logs:**
```bash
docker-compose logs -f backend
```

**Filter logs by keyword:**
```bash
docker-compose logs backend | grep -i "error"
docker-compose logs backend | grep -i "agent_node"
docker-compose logs backend | grep -i "trace_id"
```

**Last 100 lines:**
```bash
docker-compose logs --tail=100 backend
```

### Executing Commands in Container

**Interactive shell:**
```bash
docker-compose exec backend /bin/bash
```

**Run Python commands:**
```bash
docker-compose exec backend python3 -c "from app.core.config import settings; print(settings.LLM_MODEL)"
```

**Run tests:**
```bash
docker-compose exec backend python3 -m pytest tests/unit/ -v
```

### Inspecting Container State

**Check running processes:**
```bash
docker-compose exec backend ps aux
```

**Check environment variables:**
```bash
docker-compose exec backend env | grep -E "(LLM|DATABASE|LOG)"
```

---

## Enhanced Logging for Debugging

We've implemented comprehensive logging that makes debugging easier. All exceptions now include:

- **Exception type and message**
- **Duration** of operation
- **Timeout values** (step_timeout, reference timeout)
- **Langfuse trace ID** (for correlation)
- **Full stack traces** (for non-GeneratorExit exceptions)
- **Context**: agent_type, analysis_id, handled_gracefully flag

### Using Logs for Debugging

**1. Find errors by trace ID:**
```bash
docker-compose logs backend | grep "4f6b004a-641e-49e1-8ab1-d294a358c0c5"
```

**2. Find all GeneratorExit occurrences:**
```bash
docker-compose logs backend | grep "agent_node_cancelled\|agent_stream_cancelled"
```

**3. Find all errors for a specific analysis:**
```bash
docker-compose logs backend | grep "analysis_id=397a1f79-70ea-438b-852c-df28e05ccdf4"
```

**4. Find slow operations:**
```bash
docker-compose logs backend | grep "duration_seconds" | awk -F'duration_seconds=' '{print $2}' | sort -n
```

**5. Find errors with full context:**
```bash
docker-compose logs backend | grep -A 5 "agent_node_failed\|agent_stream_error"
```

### Log Levels

Set `LOG_LEVEL=DEBUG` in `backend/.env` for maximum verbosity:
```bash
LOG_LEVEL=DEBUG
```

Available levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

---

## Langfuse Trace Correlation

### Finding Trace IDs in Logs

All workflow operations now log Langfuse trace IDs when available. Look for `trace_id` in log entries:

```bash
docker-compose logs backend | grep "trace_id"
```

### Correlating Logs with Langfuse

1. **Get trace ID from Langfuse UI** (from the trace URL)
2. **Search logs for that trace ID:**
   ```bash
   docker-compose logs backend | grep "4f6b004a-641e-49e1-8ab1-d294a358c0c5"
   ```
3. **Review all operations for that trace:**
   - Agent node starts/completions
   - Exceptions and errors
   - Duration information
   - Timeout values

### Example Log Entry

```
[info] agent_node_started agent_type=tech_comparator analysis_id=397a1f79-70ea-438b-852c-df28e05ccdf4 trace_id=4f6b004a-641e-49e1-8ab1-d294a358c0c5
[warning] agent_node_cancelled agent_type=tech_comparator \
  analysis_id=397a1f79-70ea-438b-852c-df28e05ccdf4 \
  exception_type=GeneratorExit duration_seconds=45.2 step_timeout=90.0 \
  trace_id=4f6b004a-641e-49e1-8ab1-d294a358c0c5 handled_gracefully=True
```

---

## Langfuse Trace Visibility Issues

### Problem: Traces Not Appearing in Langfuse UI

**Symptoms:**
- `LANGCHAIN_TRACING_V2=true` is set
- Application logs show `langfuse_enabled=True`
- No traces appear in Langfuse UI
- Logs show `POST /runs/multipart HTTP/1.1" 202` (traces accepted by server)

**Root Cause:**
LangChain's tracing system requires `LANGCHAIN_API_KEY` to authenticate with Langfuse, even if `LANGFUSE_PUBLIC_KEY` is set. The application will automatically use `LANGFUSE_PUBLIC_KEY` as a fallback, but it's recommended to set both explicitly.

### Troubleshooting Steps

**1. Check API Key Configuration:**

```bash
# Check container environment variables
docker-compose exec backend env | grep -E "(LANGCHAIN|LANGFUSE)"

# Expected output:
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=lsv2_pt_...
# LANGFUSE_PUBLIC_KEY=lsv2_pt_...
# LANGCHAIN_PROJECT=skillforge-backend
```

**2. Check Startup Logs for Diagnostics:**

```bash
# Look for Langfuse connection diagnostics in startup logs
docker-compose logs backend | grep -E "(langfuse_connection|langfuse_api_key|application_startup)"

# Expected successful output:
# [info] langfuse_connection_success langfuse_enabled=True langfuse_project=skillforge-backend api_key_set=True
# [info] application_startup langfuse_enabled=True langchain_api_key_set=True langfuse_api_key_set=True
```

**3. Check for Warnings/Errors:**

```bash
# Look for API key warnings
docker-compose logs backend | grep -E "(langfuse_api_key_fallback|langfuse_api_key_missing|langfuse_connection_failed)"

# If you see "langfuse_api_key_fallback":
#   → LANGCHAIN_API_KEY is missing, using LANGFUSE_PUBLIC_KEY (this is OK, but set both explicitly)
#
# If you see "langfuse_api_key_missing":
#   → Neither key is set - add LANGCHAIN_API_KEY or LANGFUSE_PUBLIC_KEY to .env
#
# If you see "langfuse_connection_failed":
#   → API key is invalid or network issue - check API key and connectivity
```

**4. Verify API Key in .env File:**

```bash
# Check your .env file
cat backend/.env | grep -E "(LANGCHAIN|LANGFUSE)"

# Both should be set (can use same value):
# LANGCHAIN_API_KEY=lsv2_pt_...
# LANGFUSE_PUBLIC_KEY=lsv2_pt_...
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_PROJECT=skillforge-backend
```

**5. Test Langfuse Connection Manually:**

```bash
# Test connection from container
docker-compose exec backend python3 -c "
from langfuse import Client
import os
client = Client()
print('API Key:', 'SET' if os.getenv('LANGCHAIN_API_KEY') or os.getenv('LANGFUSE_PUBLIC_KEY') else 'NOT SET')
print('Connection test:', 'SUCCESS' if client.info else 'FAILED')
"
```

### Solution: Set Both API Keys

**Option 1: Set Both Explicitly (Recommended)**

Add to `backend/.env`:
```bash
# Get your API key from https://smith.langchain.com/settings
LANGFUSE_PUBLIC_KEY=lsv2_pt_...
LANGCHAIN_API_KEY=lsv2_pt_...  # Can be same value as LANGFUSE_PUBLIC_KEY
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=skillforge-backend
```

**Option 2: Rely on Automatic Fallback**

The application will automatically use `LANGFUSE_PUBLIC_KEY` if `LANGCHAIN_API_KEY` is missing, but you'll see a warning in logs. It's better to set both explicitly.

**After Fixing:**

1. **Restart the backend container:**
   ```bash
   docker-compose restart backend
   ```

2. **Verify startup logs show success:**
   ```bash
   docker-compose logs backend | grep "langfuse_connection_success"
   ```

3. **Trigger a workflow and check Langfuse UI:**
   - Traces should appear under the project name specified in `LANGCHAIN_PROJECT`
   - Look for traces in https://smith.langchain.com

### Common Issues

**Issue: "langfuse_api_key_missing" error**
- **Cause:** Neither `LANGCHAIN_API_KEY` nor `LANGFUSE_PUBLIC_KEY` is set
- **Fix:** Add at least `LANGFUSE_PUBLIC_KEY` to `.env` (fallback will work) or set both explicitly

**Issue: "langfuse_connection_failed" error**
- **Cause:** Invalid API key or network connectivity issue
- **Fix:** Verify API key is correct at https://smith.langchain.com/settings, check network connectivity

**Issue: Traces accepted (HTTP 202) but not visible in UI**
- **Cause:** Usually an API key authentication issue - traces are accepted but not associated with your account
- **Fix:** Ensure `LANGCHAIN_API_KEY` is set correctly (not just `LANGFUSE_PUBLIC_KEY`)

**Issue: Traces appear in different project**
- **Cause:** `LANGCHAIN_PROJECT` is set to a different project name
- **Fix:** Check `LANGCHAIN_PROJECT` value matches the project name in Langfuse UI

---

## Langfuse Studio Local Debugging

Langfuse Studio is an interactive IDE for debugging LangGraph workflows locally. It provides visual debugging, step-through execution, state inspection, and trace visualization.

### Architecture

Langfuse Studio runs as a separate development server alongside FastAPI:

```
┌─────────────────────────────────────────────────────────────┐
│              SHARED WORKFLOW LIBRARY                         │
│  backend/app/workflows/                                      │
│    ├─ analysis.py → analysis_workflow (StateGraph)          │
│    └─ tutor/graph_builder.py → tutor_workflow (StateGraph)  │
└─────────────────────────────────────────────────────────────┘
           │                              │
    ┌──────▼──────┐              ┌─────────▼─────────┐
    │   FastAPI   │              │  LangGraph CLI   │
    │  (port 8000)│              │  (port 8123)     │
    │  Production │              │  Studio Debug    │
    └──────┬──────┘              └─────────┬────────┘
           │                              │
    ┌──────▼──────────────────────────────▼──────┐
    │         PostgreSQL (Shared)                 │
    │  - Different thread_ids prevent conflicts   │
    │  - Studio uses test IDs, FastAPI uses       │
    │    analysis_id/session_id as thread_id      │
    └─────────────────────────────────────────────┘
           │                              │
           └──────────────┬───────────────┘
                          │
                  ┌───────▼────────┐
                  │  Langfuse     │
                  │  Cloud Tracing │
                  └─────────────────┘

Studio UI (port 2024) → LangGraph CLI (8123)
```

**Key Points:**
- **Separate Servers**: FastAPI (8000) and LangGraph CLI (8123) run independently
- **Shared Code**: Both import the same StateGraph workflow objects
- **Shared Database**: Both can use PostgreSQL with different `thread_id` values
- **No Conflicts**: Different ports and thread isolation prevent conflicts

### Setup

**Prerequisites:**
- Python 3.13 installed locally
- Backend dependencies installed (`poetry install` in `backend/` directory)
- Database accessible (either local PostgreSQL or Docker postgres running)
- Langfuse API keys configured in `backend/.env`

**Steps:**

1. **Set up Studio debugging environment** (recommended - avoids dependency conflicts):
   ```bash
   # From project root
   ./scripts/setup-studio-env.sh
   ```
   
   This creates a separate virtual environment (`.venv-studio`) with `langgraph-cli` installed, avoiding conflicts with FastAPI's `sse-starlette ^3.0.3` requirement.

2. **Alternative: Manual setup** (if you prefer):
   ```bash
   cd backend
   poetry install
   poetry run pip install "langgraph-cli[inmem]"
   ```
   
   **Note**: This will downgrade `sse-starlette` from 3.0.3 to 2.1.3, which may break FastAPI. Use the separate environment approach above to avoid this issue.

3. **Verify environment configuration** in `backend/.env`:
   ```bash
   # Required for Studio debugging
   LANGFUSE_PUBLIC_KEY=lsv2_pt_...
   LANGCHAIN_API_KEY=lsv2_pt_...  # Can be same as LANGFUSE_PUBLIC_KEY
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_PROJECT=skillforge-backend
   DATABASE_URL=postgresql://...  # Optional: Studio can use in-memory checkpointer
   ```

3. **Start LangGraph dev server**:
   
   **Option A: Using the convenience script** (recommended):
   ```bash
   # From project root
   ./scripts/run-studio.sh
   ```
   
   **Option B: Manual activation**:
   ```bash
   # Activate Studio environment
   source backend/.venv-studio/bin/activate
   
   # Start dev server
   cd backend
   langgraph dev
   ```
   
   This will:
   - Start the dev server on port 8123 (default)
   - Automatically open Studio UI at `http://127.0.0.1:2024` in your browser
   - Load workflows from `langgraph.json` configuration

4. **Connect Studio UI to local endpoint**:
   - Studio UI should open automatically
   - If not, navigate to `http://127.0.0.1:2024`
   - The UI will connect to `http://localhost:8123` by default
   - Select workflow (analysis or tutor) from the dropdown

### Usage

**Running Workflows:**

1. **Select a workflow** from the dropdown (analysis or tutor)

2. **Provide input** matching the workflow's state schema:
   - **Analysis workflow**: `{"url": "https://example.com/article", "analysis_id": "test-123"}`
   - **Tutor workflow**: `{"session_id": "test-session", "artifact_id": "test-artifact", ...}`

3. **Run the workflow**:
   - Click "Run" to execute the workflow
   - Use "Step" to execute one node at a time
   - Use "Continue" to resume after a step

4. **Inspect state**:
   - View state at each step in the UI
   - See node inputs and outputs
   - Inspect checkpoints and state history

5. **View traces**:
   - Traces automatically appear in Langfuse cloud UI
   - Same project as FastAPI traces (`LANGCHAIN_PROJECT`)
   - Full trace correlation with Studio execution

### When to Use Studio vs FastAPI

**Use Langfuse Studio for:**
- Interactive debugging and step-through execution
- State inspection at each workflow step
- Testing workflow logic without full API integration
- Visualizing workflow execution flow
- Debugging specific nodes or routing logic
- Prototyping workflow changes

**Use FastAPI for:**
- Production API endpoints
- SSE streaming to frontend
- Full integration testing with database
- Testing complete request/response cycle
- Performance testing under load
- End-to-end user flow validation

### Thread ID Isolation

Studio and FastAPI can run simultaneously without conflicts:

- **Studio**: Uses auto-generated thread IDs for test runs (e.g., `studio-thread-123`)
- **FastAPI**: Uses `analysis_id` or `session_id` as thread_id (e.g., `397a1f79-70ea-438b-852c-df28e05ccdf4`)
- **No Conflicts**: Thread IDs are unique, so checkpoints don't interfere
- **Same Database**: Both can use PostgreSQL with different thread namespaces

### Cloning Remote Traces for Local Testing

You can replay traces from Langfuse cloud in Studio:

1. **Open trace in Langfuse cloud UI**:
   - Navigate to https://smith.langchain.com
   - Open the trace you want to debug

2. **Clone to Studio**:
   - Click "Run in Studio" button
   - Enter your local endpoint: `http://localhost:8123`
   - Click "Clone thread locally"
   - Studio creates a new thread with the same state history

3. **Debug locally**:
   - Workflow state is restored from the remote trace
   - You can step through execution locally
   - Make changes to workflow code and test
   - Traces from local execution appear in same Langfuse project

### Dependency Conflict Resolution

**The Issue:**
- `langgraph-cli` requires `sse-starlette <2.2.0`
- SkillForge FastAPI requires `sse-starlette ^3.0.3`
- These cannot coexist in the same Python environment

**The Solution:**
We use a separate virtual environment (`.venv-studio`) for Studio debugging:
- Studio environment: Has `langgraph-cli` with `sse-starlette 2.1.3`
- Main environment: Has FastAPI with `sse-starlette 3.0.3`
- Both can run simultaneously without conflicts

**If you need to reinstall Studio environment:**
```bash
# Remove old environment
rm -rf backend/.venv-studio

# Recreate it
./scripts/setup-studio-env.sh
```

### Troubleshooting

**Port Conflicts:**

If port 8123 is already in use:
```bash
# Use a different port
langgraph dev --port 8124
```

Then update Studio UI connection to `http://localhost:8124`

**Database Connection Issues:**

If PostgreSQL is not accessible, Studio will fall back to in-memory checkpointer:
- State is not persisted between runs
- This is fine for debugging individual workflow executions
- For persistent state, ensure `DATABASE_URL` is set correctly

**Environment Variable Loading:**

If environment variables aren't loading:
```bash
# Verify .env file is in backend/ directory
ls backend/.env

# Check that langgraph.json points to .env
cat backend/langgraph.json | grep env
# Should show: "env": ".env"
```

**Workflow Import Errors:**

If workflows don't appear in Studio dropdown:
```bash
# Test imports manually
cd backend
python3 -c "from app.workflows.analysis import analysis_workflow; print('Analysis workflow OK')"
python3 -c "from app.workflows.tutor.graph_builder import tutor_workflow; print('Tutor workflow OK')"
```

If imports fail, check:
- `PYTHONPATH` includes `backend/` directory
- All dependencies are installed (`poetry install`)
- Workflow files are in correct locations

**Studio UI Not Opening:**

If Studio UI doesn't open automatically:
- Manually navigate to `http://127.0.0.1:2024`
- Check terminal output for the Studio URL
- Verify no firewall is blocking the port

**Traces Not Appearing in Langfuse:**

If traces from Studio don't appear in Langfuse cloud:
- Verify `LANGCHAIN_TRACING_V2=true` in `.env`
- Verify `LANGCHAIN_API_KEY` is set correctly
- Check Studio terminal output for Langfuse connection errors
- Ensure `LANGCHAIN_PROJECT` matches your Langfuse project name

### Step-Through Debugging with VS Code

For advanced debugging with breakpoints in VS Code:

1. **Start LangGraph dev server with debug port**:
   ```bash
   cd backend
   langgraph dev --debug-port 2025
   ```

2. **Attach VS Code debugger**:
   - Use the "LangGraph Studio Debug" configuration (see `.vscode/launch.json`)
   - Set breakpoints in workflow code
   - Debugger will stop at breakpoints during Studio execution

See [VS Code Debugging](#vs-code-debugging) section for more details.

---

## Common Debugging Scenarios

### Scenario 1: Workflow Hangs or Times Out

**Symptoms:**
- Workflow doesn't complete
- Langfuse shows GeneratorExit
- No errors in logs

**Debugging Steps:**

1. **Check step_timeout value:**
   ```bash
   docker-compose logs backend | grep "step_timeout"
   ```

2. **Find which agent is slow:**
   ```bash
   docker-compose logs backend | grep "duration_seconds" | sort -t= -k2 -n
   ```

3. **Check for GeneratorExit:**
   ```bash
   docker-compose logs backend | grep "GeneratorExit\|agent_node_cancelled"
   ```

4. **Review timeout configuration:**
   - Check `backend/app/core/timeout_config.py`
   - Verify `STEP_TIMEOUT` value (currently 90.0s)

### Scenario 2: Agent Returns Empty Results

**Symptoms:**
- Agent completes but returns empty findings
- No errors in logs

**Debugging Steps:**

1. **Check if agent was cancelled:**
   ```bash
   docker-compose logs backend | grep "agent_node_cancelled\|agent_stream_cancelled"
   ```

2. **Check for exceptions:**
   ```bash
   docker-compose logs backend | grep "agent_node_failed\|agent_stream_error"
   ```

3. **Check agent execution duration:**
   ```bash
   docker-compose logs backend | grep "agent_node_complete" | grep "duration_seconds"
   ```

### Scenario 3: LLM Calls Fail

**Symptoms:**
- Errors in logs about LLM calls
- Timeout errors

**Debugging Steps:**

1. **Check model configuration:**
   ```bash
   docker-compose logs backend | grep "chat_model_initializing"
   ```

2. **Check retry configuration:**
   ```bash
   docker-compose logs backend | grep "max_retries"
   ```

3. **Check timeout values:**
   ```bash
   docker-compose logs backend | grep "timeout="
   ```

4. **Review error details:**
   ```bash
   docker-compose logs backend | grep -A 10 "agent_invocation_error"
   ```

### Scenario 4: Database Connection Issues

**Symptoms:**
- Database errors in logs
- Connection timeouts

**Debugging Steps:**

1. **Check database connectivity:**
   ```bash
   docker-compose exec backend python3 -c "from app.db.session import engine; import asyncio; asyncio.run(engine.connect())"
   ```

2. **Check database URL:**
   ```bash
   docker-compose exec backend env | grep DATABASE_URL
   ```

3. **Test database connection:**
   ```bash
   docker-compose exec postgres psql -U dev -d skillforge -c "SELECT 1;"
   ```

---

## Quick Reference

### Most Useful Commands

```bash
# Watch logs in real-time
docker-compose logs -f backend

# Find errors
docker-compose logs backend | grep -i error

# Find by trace ID
docker-compose logs backend | grep "TRACE_ID_HERE"

# Find by analysis ID
docker-compose logs backend | grep "analysis_id=ANALYSIS_ID_HERE"

# Find slow operations
docker-compose logs backend | grep "duration_seconds" | sort -t= -k2 -n | tail -10

# Find all exceptions
docker-compose logs backend | grep -E "(exception_type|error_type)"

# Get last 50 lines
docker-compose logs --tail=50 backend
```

### VS Code Debugging Shortcuts

- **F5**: Start/Continue debugging
- **F9**: Toggle breakpoint
- **F10**: Step over
- **F11**: Step into
- **Shift+F11**: Step out
- **Shift+F5**: Stop debugging
- **Cmd+Shift+D**: Open Run and Debug panel

---

## Tips

1. **Use structured logging**: All logs are structured JSON in production, making them easy to parse and search
2. **Correlate with Langfuse**: Use trace IDs to correlate application logs with Langfuse traces
3. **Check duration**: Slow operations are logged with `duration_seconds` - use this to identify bottlenecks
4. **Review error context**: All errors include full context (agent_type, analysis_id, timeout values, etc.)
5. **GeneratorExit is normal**: GeneratorExit appears in Langfuse traces but is handled gracefully - check logs for `handled_gracefully=True`

---

**Last Updated**: 2025-11-29
**Related Files**: 
- `.vscode/launch.json` - VS Code debugging configuration
- `backend/app/core/logging.py` - Logging setup
- `backend/app/workflows/agents/streaming.py` - Enhanced error logging
- `backend/app/workflows/agents/invocation.py` - Enhanced error logging
