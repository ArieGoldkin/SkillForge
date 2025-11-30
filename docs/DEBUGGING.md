# Backend Debugging Guide

This guide covers multiple approaches to debug the SkillForge backend.

## Table of Contents

1. [VS Code Debugging](#vs-code-debugging)
2. [Docker Container Debugging](#docker-container-debugging)
3. [Enhanced Logging for Debugging](#enhanced-logging-for-debugging)
4. [LangSmith Trace Correlation](#langsmith-trace-correlation)
5. [LangSmith Studio Local Debugging](#langsmith-studio-local-debugging)
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
- **LangSmith trace ID** (for correlation)
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

## LangSmith Trace Correlation

### Finding Trace IDs in Logs

All workflow operations now log LangSmith trace IDs when available. Look for `trace_id` in log entries:

```bash
docker-compose logs backend | grep "trace_id"
```

### Correlating Logs with LangSmith

1. **Get trace ID from LangSmith UI** (from the trace URL)
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
[warning] agent_node_cancelled agent_type=tech_comparator analysis_id=397a1f79-70ea-438b-852c-df28e05ccdf4 exception_type=GeneratorExit duration_seconds=45.2 step_timeout=90.0 trace_id=4f6b004a-641e-49e1-8ab1-d294a358c0c5 handled_gracefully=True
```

---

## LangSmith Trace Visibility Issues

### Problem: Traces Not Appearing in LangSmith UI

**Symptoms:**
- `LANGCHAIN_TRACING_V2=true` is set
- Application logs show `langsmith_enabled=True`
- No traces appear in LangSmith UI
- Logs show `POST /runs/multipart HTTP/1.1" 202` (traces accepted by server)

**Root Cause:**
LangChain's tracing system requires `LANGCHAIN_API_KEY` to authenticate with LangSmith, even if `LANGSMITH_API_KEY` is set. The application will automatically use `LANGSMITH_API_KEY` as a fallback, but it's recommended to set both explicitly.

### Troubleshooting Steps

**1. Check API Key Configuration:**

```bash
# Check container environment variables
docker-compose exec backend env | grep -E "(LANGCHAIN|LANGSMITH)"

# Expected output:
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=lsv2_pt_...
# LANGSMITH_API_KEY=lsv2_pt_...
# LANGCHAIN_PROJECT=skillforge-backend
```

**2. Check Startup Logs for Diagnostics:**

```bash
# Look for LangSmith connection diagnostics in startup logs
docker-compose logs backend | grep -E "(langsmith_connection|langsmith_api_key|application_startup)"

# Expected successful output:
# [info] langsmith_connection_success langsmith_enabled=True langsmith_project=skillforge-backend api_key_set=True
# [info] application_startup langsmith_enabled=True langchain_api_key_set=True langsmith_api_key_set=True
```

**3. Check for Warnings/Errors:**

```bash
# Look for API key warnings
docker-compose logs backend | grep -E "(langsmith_api_key_fallback|langsmith_api_key_missing|langsmith_connection_failed)"

# If you see "langsmith_api_key_fallback":
#   → LANGCHAIN_API_KEY is missing, using LANGSMITH_API_KEY (this is OK, but set both explicitly)
#
# If you see "langsmith_api_key_missing":
#   → Neither key is set - add LANGCHAIN_API_KEY or LANGSMITH_API_KEY to .env
#
# If you see "langsmith_connection_failed":
#   → API key is invalid or network issue - check API key and connectivity
```

**4. Verify API Key in .env File:**

```bash
# Check your .env file
cat backend/.env | grep -E "(LANGCHAIN|LANGSMITH)"

# Both should be set (can use same value):
# LANGCHAIN_API_KEY=lsv2_pt_...
# LANGSMITH_API_KEY=lsv2_pt_...
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_PROJECT=skillforge-backend
```

**5. Test LangSmith Connection Manually:**

```bash
# Test connection from container
docker-compose exec backend python3 -c "
from langsmith import Client
import os
client = Client()
print('API Key:', 'SET' if os.getenv('LANGCHAIN_API_KEY') or os.getenv('LANGSMITH_API_KEY') else 'NOT SET')
print('Connection test:', 'SUCCESS' if client.info else 'FAILED')
"
```

### Solution: Set Both API Keys

**Option 1: Set Both Explicitly (Recommended)**

Add to `backend/.env`:
```bash
# Get your API key from https://smith.langchain.com/settings
LANGSMITH_API_KEY=lsv2_pt_...
LANGCHAIN_API_KEY=lsv2_pt_...  # Can be same value as LANGSMITH_API_KEY
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=skillforge-backend
```

**Option 2: Rely on Automatic Fallback**

The application will automatically use `LANGSMITH_API_KEY` if `LANGCHAIN_API_KEY` is missing, but you'll see a warning in logs. It's better to set both explicitly.

**After Fixing:**

1. **Restart the backend container:**
   ```bash
   docker-compose restart backend
   ```

2. **Verify startup logs show success:**
   ```bash
   docker-compose logs backend | grep "langsmith_connection_success"
   ```

3. **Trigger a workflow and check LangSmith UI:**
   - Traces should appear under the project name specified in `LANGCHAIN_PROJECT`
   - Look for traces in https://smith.langchain.com

### Common Issues

**Issue: "langsmith_api_key_missing" error**
- **Cause:** Neither `LANGCHAIN_API_KEY` nor `LANGSMITH_API_KEY` is set
- **Fix:** Add at least `LANGSMITH_API_KEY` to `.env` (fallback will work) or set both explicitly

**Issue: "langsmith_connection_failed" error**
- **Cause:** Invalid API key or network connectivity issue
- **Fix:** Verify API key is correct at https://smith.langchain.com/settings, check network connectivity

**Issue: Traces accepted (HTTP 202) but not visible in UI**
- **Cause:** Usually an API key authentication issue - traces are accepted but not associated with your account
- **Fix:** Ensure `LANGCHAIN_API_KEY` is set correctly (not just `LANGSMITH_API_KEY`)

**Issue: Traces appear in different project**
- **Cause:** `LANGCHAIN_PROJECT` is set to a different project name
- **Fix:** Check `LANGCHAIN_PROJECT` value matches the project name in LangSmith UI

---

## Common Debugging Scenarios

### Scenario 1: Workflow Hangs or Times Out

**Symptoms:**
- Workflow doesn't complete
- LangSmith shows GeneratorExit
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
2. **Correlate with LangSmith**: Use trace IDs to correlate application logs with LangSmith traces
3. **Check duration**: Slow operations are logged with `duration_seconds` - use this to identify bottlenecks
4. **Review error context**: All errors include full context (agent_type, analysis_id, timeout values, etc.)
5. **GeneratorExit is normal**: GeneratorExit appears in LangSmith traces but is handled gracefully - check logs for `handled_gracefully=True`

---

**Last Updated**: 2025-11-29
**Related Files**: 
- `.vscode/launch.json` - VS Code debugging configuration
- `backend/app/core/logging.py` - Logging setup
- `backend/app/workflows/agents/streaming.py` - Enhanced error logging
- `backend/app/workflows/agents/invocation.py` - Enhanced error logging
