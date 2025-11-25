# SSE Endpoint Manual Testing Guide

**Date:** November 23, 2025  
**Status:** ⚠️ **NOT YET VERIFIED**  
**Issue:** #40 - SSE Endpoint Implementation

---

## ⚠️ Current Status

**The SSE endpoint has NOT been verified with real data in a dev environment.**

### Test Limitations

The current integration tests (`tests/integration/test_sse_endpoint.py`) have the following limitations:

1. **No Real HTTP Streaming:** Tests use direct function calls instead of HTTP requests due to `httpx.ASGITransport` limitations with SSE streaming
2. **No Real Workflow Execution:** Tests don't trigger actual LangGraph workflow execution
3. **Mocked Events:** Events are published directly to the broadcaster, not through workflow execution

### What's Tested

✅ **Unit Tests:**
- EventBroadcaster pub/sub functionality
- SSE helper functions
- Event formatting and schema

✅ **Integration Tests:**
- Endpoint function returns EventSourceResponse
- Broadcaster integration
- Event publishing/receiving

❌ **NOT Tested:**
- Real HTTP SSE connection
- Real workflow execution with SSE events
- End-to-end flow: API call → Workflow → SSE events → Client

---

## Manual Testing Steps

### Prerequisites

1. **Backend Server Running:**
   ```bash
   cd backend
   poetry run uvicorn app.main:app --reload --port 8500
   ```

2. **Database Running:**
   ```bash
   docker-compose up -d postgres
   ```

3. **OpenAI API Key Configured:**
   ```bash
   # Set in .env file
   OPENAI_API_KEY=sk-...
   ```

4. **Environment Variables:**
   ```bash
   # backend/.env
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/skillforge
   JINA_API_KEY=your_jina_api_key
   EMBEDDING_DIMENSIONS=1536
   ```

### Test 1: SSE Connection (Browser)

1. **Open browser console** (Chrome DevTools)
2. **Connect to SSE endpoint:**
   ```javascript
   const analysisId = 'test-analysis-id-123';
   const eventSource = new EventSource(
     `http://localhost:8500/api/v1/analyze/${analysisId}/stream`
   );
   
   eventSource.addEventListener('progress', (event) => {
     console.log('Progress:', JSON.parse(event.data));
   });
   
   eventSource.addEventListener('complete', (event) => {
     console.log('Complete:', JSON.parse(event.data));
     eventSource.close();
   });
   
   eventSource.addEventListener('error', (event) => {
     console.error('Error:', event);
   });
   ```

3. **Expected:** Connection established, waiting for events

### Test 2: Trigger Workflow with SSE Events

**Note:** This requires the workflow to be integrated with the API endpoint (Issue #8 or future task).

Currently, the workflow (`app/workflows/analysis.py`) emits SSE events via `emit_streaming_event()`, but there's no API endpoint to trigger the workflow yet.

**To test manually:**

1. **In Python shell or separate script:**
   ```python
   import asyncio
   from app.workflows.analysis import analysis_workflow
   import uuid
   
   async def test_workflow_with_sse():
       analysis_id = str(uuid.uuid4())
       result = await analysis_workflow(
           url="https://react.dev",
           analysis_id=analysis_id
       )
       print(f"Workflow complete: {result}")
   
   asyncio.run(test_workflow_with_sse())
   ```

2. **While workflow runs, check browser console** for SSE events

3. **Expected Events:**
   - `progress` event: `stage: "extraction", status: "running"`
   - `progress` event: `stage: "extraction", status: "complete"`
   - `progress` event: `stage: "embedding", status: "running"`
   - `progress` event: `stage: "embedding", status: "complete"`

### Test 3: End-to-End with curl

```bash
# Terminal 1: Start SSE connection
curl -N -H "Accept: text/event-stream" \
  http://localhost:8500/api/v1/analyze/test-id-123/stream

# Terminal 2: Trigger workflow (when API endpoint exists)
curl -X POST http://localhost:8500/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://react.dev"}'
```

---

## Verification Checklist

- [ ] SSE connection establishes successfully
- [ ] Events stream in real-time during workflow execution
- [ ] Progress events received for each workflow stage
- [ ] Complete event received when workflow finishes
- [ ] Error events received on workflow failures
- [ ] Connection closes properly on complete event
- [ ] Connection handles client disconnection gracefully
- [ ] Multiple clients can connect to same analysis_id
- [ ] Events are properly formatted (JSON parseable)
- [ ] Timestamps are included in all events

---

## Known Issues

1. **No API Endpoint to Trigger Workflow:**
   - Workflow exists but no `POST /api/v1/analyze` endpoint yet
   - Need to create endpoint that triggers workflow and returns analysis_id

2. **ASGITransport Limitation:**
   - `httpx.ASGITransport` doesn't support streaming responses
   - Integration tests can't verify real HTTP SSE streaming
   - Manual testing required for full verification

3. **Workflow Integration:**
   - Workflow emits SSE events via `emit_streaming_event()`
   - But workflow is not yet called from API endpoint
   - Need to integrate workflow with API (Issue #8 or future task)

---

## Next Steps

1. **Create API Endpoint** to trigger workflow:
   ```python
   @router.post("/analyze")
   async def create_analysis(request: AnalyzeRequest):
       analysis_id = str(uuid.uuid4())
       # Trigger workflow in background
       asyncio.create_task(analysis_workflow(
           url=request.url,
           analysis_id=analysis_id
       ))
       return {"analysis_id": analysis_id}
   ```

2. **Manual Testing:**
   - Follow steps above to verify end-to-end flow
   - Document any issues found
   - Update this document with results

3. **E2E Test (Future):**
   - Create Playwright test that:
     - Starts backend server
     - Connects to SSE endpoint
     - Triggers workflow via API
     - Verifies events stream correctly

---

**Last Updated:** November 23, 2025  
**Status:** ⚠️ Manual testing not yet performed
