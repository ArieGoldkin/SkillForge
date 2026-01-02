---
name: streaming-websocket
description: WebSocket for bidirectional real-time communication
version: 1.0.0
tags: [streaming, websocket, real-time, chat]
size: atomic
domain: frontend
---

# WebSocket Streaming

**Best for**: Bidirectional real-time (chat, collaboration)

## Server

```typescript
import { WebSocketServer } from 'ws'

const wss = new WebSocketServer({ port: 8080 })

wss.on('connection', (ws) => {
  ws.on('message', (data) => {
    // Broadcast to all clients
    wss.clients.forEach((client) => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(data)
      }
    })
  })

  ws.on('close', () => {
    console.log('Client disconnected')
  })
})
```

## Client

```typescript
const ws = new WebSocket('ws://localhost:8080')

ws.onopen = () => {
  console.log('Connected')
}

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  console.log(data)
}

ws.onclose = () => {
  console.log('Disconnected')
}

// Send message
ws.send(JSON.stringify({ type: 'message', text: 'Hello' }))
```

## React Hook

```typescript
function useWebSocket(url: string) {
  const [messages, setMessages] = useState<Message[]>([])
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onmessage = (event) => {
      setMessages(prev => [...prev, JSON.parse(event.data)])
    }

    return () => ws.close()
  }, [url])

  const send = useCallback((data: object) => {
    wsRef.current?.send(JSON.stringify(data))
  }, [])

  return { messages, send }
}
```

## Best Practices

- ✅ Implement heartbeat/ping-pong
- ✅ Reconnect with exponential backoff
- ✅ Validate and sanitize messages
- ✅ Queue messages during offline
- ✅ Handle connection state in UI
