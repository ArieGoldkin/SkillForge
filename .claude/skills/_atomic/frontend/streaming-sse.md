---
name: streaming-sse
description: Server-Sent Events for server-to-client streaming
version: 1.0.0
tags: [streaming, sse, real-time, api]
size: atomic
domain: frontend
---

# Server-Sent Events (SSE)

**Best for**: Server-to-client streaming (LLM responses, notifications)

## Server (Next.js Route Handler)

```typescript
export async function GET(req: Request) {
  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    async start(controller) {
      // Send data
      controller.enqueue(encoder.encode('data: Hello\n\n'))

      // Keep connection alive
      const interval = setInterval(() => {
        controller.enqueue(encoder.encode(': keepalive\n\n'))
      }, 30000)

      // Cleanup on disconnect
      req.signal.addEventListener('abort', () => {
        clearInterval(interval)
        controller.close()
      })
    }
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    }
  })
}
```

## Client

```typescript
const eventSource = new EventSource('/api/stream')

eventSource.onmessage = (event) => {
  console.log(event.data)
}

eventSource.onerror = () => {
  eventSource.close()
}
```

## Reconnecting EventSource

```typescript
class ReconnectingEventSource {
  private eventSource: EventSource | null = null
  private reconnectDelay = 1000
  private maxDelay = 30000

  constructor(private url: string, private onMessage: (data: string) => void) {
    this.connect()
  }

  private connect() {
    this.eventSource = new EventSource(this.url)

    this.eventSource.onmessage = (event) => {
      this.reconnectDelay = 1000  // Reset on success
      this.onMessage(event.data)
    }

    this.eventSource.onerror = () => {
      this.eventSource?.close()
      setTimeout(() => this.connect(), this.reconnectDelay)
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxDelay)
    }
  }

  close() { this.eventSource?.close() }
}
```

## Best Practices

- ✅ Send keepalive every 30s
- ✅ Implement automatic reconnection
- ✅ Handle browser limits (6 connections/domain)
- ✅ Use HTTP/2 for better performance
