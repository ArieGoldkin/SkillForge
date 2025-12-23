# Alternatives to Server-Sent Events (SSE)

## Current Architecture

**Use Case**: One-way server-to-client streaming of workflow progress events for long-running analysis tasks.

**Current Stack**:
- Backend: FastAPI + `sse-starlette` + EventBroadcaster (Redis Pub/Sub or in-memory)
- Frontend: EventSource API + Zustand store
- Pattern: Workflow nodes emit events → EventBroadcaster → SSE endpoint → Frontend

---

## Alternative Options

### 1. WebSockets ⭐ (Most Common Alternative)

**Best for**: When you need bidirectional communication or more control over the connection.

#### Pros
- ✅ Bidirectional communication (can send commands from client)
- ✅ Lower latency than SSE
- ✅ Better for high-frequency updates
- ✅ More control over connection lifecycle
- ✅ Can send binary data
- ✅ Works well with existing EventBroadcaster (just change transport)

#### Cons
- ❌ More complex to implement (connection management, ping/pong)
- ❌ Higher server resource usage (persistent connections)
- ❌ Requires WebSocket library (e.g., `websockets`, `fastapi-websockets`)
- ❌ More complex error handling and reconnection logic

#### Implementation Example

**Backend** (`backend/app/api/v1/analysis/websocket_handler.py`):
```python
from fastapi import WebSocket, WebSocketDisconnect
from app.shared.services.messaging.broadcaster_factory import get_broadcaster
from contextlib import aclosing

@router.websocket("/analyze/{analysis_id}/ws")
async def websocket_analysis_progress(
    websocket: WebSocket,
    analysis_id: uuid.UUID,
):
    """Stream real-time analysis progress via WebSocket."""
    await websocket.accept()
    channel = f"workflow:{analysis_id}"
    
    try:
        broadcaster = await get_broadcaster(_get_broadcaster_backend())
        
        async with aclosing(broadcaster.subscribe(channel)) as subscription:
            async for event in subscription:
                await websocket.send_json(event)
                
                if event.get("type") == "complete":
                    break
                    
    except WebSocketDisconnect:
        logger.info("websocket_client_disconnected", analysis_id=str(analysis_id))
    except Exception as e:
        logger.error("websocket_error", analysis_id=str(analysis_id), error=str(e))
        await websocket.close(code=1011, reason="Internal error")
```

**Frontend** (`frontend/src/features/analysis/hooks/useWebSocketConnection.ts`):
```typescript
import { useEffect, useRef, useState } from 'react'

export function useWebSocketConnection(analysisId: string | null) {
  const [events, setEvents] = useState<SSEEvent[]>([])
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const reconnectAttempts = useRef(0)

  useEffect(() => {
    if (!analysisId) return

    const connect = () => {
      const ws = new WebSocket(`ws://localhost:8500/api/v1/analyze/${analysisId}/ws`)
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data) as SSEEvent
        setEvents(prev => [...prev, data])
      }
      
      ws.onclose = () => {
        // Exponential backoff reconnection
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
        reconnectTimeoutRef.current = window.setTimeout(() => {
          reconnectAttempts.current++
          connect()
        }, delay)
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
      
      wsRef.current = ws
    }

    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      wsRef.current?.close()
    }
  }, [analysisId])

  return { events }
}
```

**Dependencies**:
```bash
# Backend
poetry add websockets fastapi-websockets

# Frontend (no additional deps - WebSocket is native)
```

---

### 2. Long Polling 🔄 (Simple Fallback)

**Best for**: When SSE/WebSockets are blocked by firewalls or you need maximum compatibility.

#### Pros
- ✅ Works through all firewalls and proxies
- ✅ Simple to implement (just HTTP GET with timeout)
- ✅ No persistent connections (less server resources)
- ✅ Easy to add retry logic
- ✅ Works with existing EventBroadcaster (poll from cache/DB)

#### Cons
- ❌ Higher latency (polling interval)
- ❌ More HTTP requests (higher overhead)
- ❌ Less efficient than SSE/WebSockets
- ❌ Requires event buffering (miss events between polls)

#### Implementation Example

**Backend** (`backend/app/api/v1/analysis/polling_handler.py`):
```python
from fastapi import Query
from app.db.repositories.progress import get_progress_repository

@router.get("/analyze/{analysis_id}/poll")
async def poll_analysis_progress(
    analysis_id: uuid.UUID,
    since: datetime | None = Query(None, description="Get events since this timestamp"),
    timeout: int = Query(30, ge=5, le=60, description="Max seconds to wait for new events"),
) -> dict:
    """Long polling endpoint for analysis progress.
    
    Returns new events since `since` timestamp. If no events, waits up to `timeout`
    seconds before returning empty list (long polling).
    """
    repo = get_progress_repository()
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        events = await repo.get_events_since(analysis_id, since)
        
        if events:
            return {
                "events": events,
                "next_poll_after": 0,  # Immediate next poll
            }
        
        # Wait 1 second before checking again
        await asyncio.sleep(1)
    
    # Timeout - return empty with next poll delay
    return {
        "events": [],
        "next_poll_after": 2,  # Poll again in 2 seconds
    }
```

**Frontend** (`frontend/src/features/analysis/hooks/useLongPolling.ts`):
```typescript
import { useEffect, useRef, useState } from 'react'

export function useLongPolling(analysisId: string | null) {
  const [events, setEvents] = useState<SSEEvent[]>([])
  const lastEventTimeRef = useRef<Date | null>(null)
  const pollingRef = useRef<number | null>(null)

  useEffect(() => {
    if (!analysisId) return

    const poll = async () => {
      try {
        const since = lastEventTimeRef.current?.toISOString()
        const response = await fetch(
          `/api/v1/analyze/${analysisId}/poll?since=${since || ''}&timeout=30`
        )
        const data = await response.json()
        
        if (data.events.length > 0) {
          setEvents(prev => [...prev, ...data.events])
          lastEventTimeRef.current = new Date(data.events[data.events.length - 1].timestamp)
        }
        
        // Schedule next poll
        pollingRef.current = window.setTimeout(poll, data.next_poll_after * 1000)
      } catch (error) {
        console.error('Polling error:', error)
        // Retry after 2 seconds on error
        pollingRef.current = window.setTimeout(poll, 2000)
      }
    }

    poll()

    return () => {
      if (pollingRef.current) {
        clearTimeout(pollingRef.current)
      }
    }
  }, [analysisId])

  return { events }
}
```

**Database Schema** (if not exists):
```python
# backend/app/db/models/progress.py
class ProgressEvent(Base):
    __tablename__ = "progress_events"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    analysis_id = Column(UUID, ForeignKey("analyses.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    event_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC), index=True)
```

---

### 3. HTTP Polling (Simplest, Least Efficient)

**Best for**: Maximum compatibility, simple debugging, or when real-time updates aren't critical.

#### Pros
- ✅ Simplest implementation (just GET endpoint)
- ✅ Works everywhere (no special protocols)
- ✅ Easy to debug (standard HTTP)
- ✅ No connection management
- ✅ Can use existing `/progress` endpoint

#### Cons
- ❌ Highest latency (polling interval)
- ❌ Most inefficient (constant HTTP requests)
- ❌ Higher server load
- ❌ Battery drain on mobile devices

#### Implementation Example

**Backend** (reuse existing endpoint):
```python
# Already exists: backend/app/api/v1/analysis.py
@router.get("/analyze/{analysis_id}/progress")
async def get_analysis_progress(analysis_id: uuid.UUID) -> ProgressResponse:
    """Get current analysis progress (for polling)."""
    # Existing implementation
```

**Frontend** (`frontend/src/features/analysis/hooks/usePolling.ts`):
```typescript
import { useEffect, useRef, useState } from 'react'

export function usePolling(analysisId: string | null, intervalMs = 2000) {
  const [progress, setProgress] = useState<ProgressResponse | null>(null)
  const intervalRef = useRef<number | null>(null)

  useEffect(() => {
    if (!analysisId) return

    const poll = async () => {
      try {
        const response = await fetch(`/api/v1/analyze/${analysisId}/progress`)
        const data = await response.json()
        setProgress(data)
        
        // Stop polling if complete
        if (data.status === 'complete') {
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
          }
        }
      } catch (error) {
        console.error('Polling error:', error)
      }
    }

    poll() // Immediate first poll
    intervalRef.current = window.setInterval(poll, intervalMs)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [analysisId, intervalMs])

  return { progress }
}
```

---

### 4. GraphQL Subscriptions (Overkill for This Use Case)

**Best for**: When you already have GraphQL API and need subscriptions.

#### Pros
- ✅ Unified API (queries + subscriptions)
- ✅ Type-safe with GraphQL schema
- ✅ Can filter/subscribe to specific fields

#### Cons
- ❌ Requires GraphQL infrastructure (Strawberry, Ariadne, etc.)
- ❌ More complex setup
- ❌ Overkill for simple progress updates
- ❌ Typically uses WebSockets under the hood anyway

**Not recommended** unless you're already using GraphQL.

---

## Comparison Matrix

| Feature | SSE (Current) | WebSockets | Long Polling | HTTP Polling |
|---------|---------------|------------|--------------|--------------|
| **Latency** | Low (~100ms) | Very Low (~50ms) | Medium (1-2s) | High (2-5s) |
| **Complexity** | Medium | High | Low | Very Low |
| **Server Resources** | Medium | High | Low | Medium |
| **Firewall Compatibility** | Good | Good | Excellent | Excellent |
| **Bidirectional** | ❌ | ✅ | ❌ | ❌ |
| **Reconnection** | Auto (EventSource) | Manual | Manual | N/A |
| **Browser Support** | Excellent | Excellent | Excellent | Excellent |
| **Mobile Battery** | Good | Good | Excellent | Poor |
| **Implementation Effort** | ✅ Done | 2-3 days | 1 day | 0.5 days |

---

## Recommendation

### Stick with SSE if:
- ✅ Current implementation works well
- ✅ No need for bidirectional communication
- ✅ Firewall/proxy issues are rare
- ✅ You want to avoid additional complexity

### Switch to WebSockets if:
- ✅ You need client-to-server commands (e.g., "cancel analysis")
- ✅ You need lower latency (<100ms)
- ✅ You're building chat/collaboration features
- ✅ You have WebSocket infrastructure already

### Use Long Polling if:
- ✅ SSE is blocked by corporate firewalls
- ✅ You need maximum compatibility
- ✅ Real-time updates aren't critical (1-2s delay acceptable)
- ✅ You want simpler debugging

### Use HTTP Polling if:
- ✅ Maximum simplicity is priority
- ✅ Updates are infrequent (>5s intervals)
- ✅ You're prototyping or have very low traffic

---

## Migration Path (If Switching)

### SSE → WebSockets

1. **Add WebSocket endpoint** alongside SSE (keep both for backward compatibility)
2. **Update frontend** to try WebSocket first, fallback to SSE
3. **Monitor** connection stability and errors
4. **Deprecate SSE** after WebSocket proves stable

### SSE → Long Polling

1. **Add polling endpoint** that reads from progress events table
2. **Update frontend** to use polling when SSE fails
3. **Implement exponential backoff** for reconnection
4. **Keep SSE as primary**, polling as fallback

---

## Hybrid Approach (Recommended)

**Best of both worlds**: Use SSE as primary, with automatic fallback to long polling.

```typescript
// frontend/src/features/analysis/hooks/useHybridStreaming.ts
export function useHybridStreaming(analysisId: string | null) {
  const [events, setEvents] = useState<SSEEvent[]>([])
  const [transport, setTransport] = useState<'sse' | 'polling'>('sse')
  
  // Try SSE first
  const sseResult = useSSEConnection(analysisId)
  
  // Fallback to polling if SSE fails
  useEffect(() => {
    if (sseResult.error && transport === 'sse') {
      console.warn('SSE failed, falling back to polling')
      setTransport('polling')
    }
  }, [sseResult.error, transport])
  
  const pollingResult = useLongPolling(analysisId, { enabled: transport === 'polling' })
  
  return transport === 'sse' ? sseResult : pollingResult
}
```

This gives you:
- ✅ Real-time updates when SSE works
- ✅ Automatic fallback for firewall issues
- ✅ Best user experience in all scenarios

---

## References

- **Current SSE Implementation**: `backend/app/api/v1/analysis/sse_handler.py`
- **EventBroadcaster**: `backend/app/shared/services/messaging/broadcaster_factory.py`
- **Frontend SSE Store**: `frontend/src/stores/sseStore.ts`
- **Streaming Patterns Skill**: `.claude/skills/streaming-api-patterns/`
