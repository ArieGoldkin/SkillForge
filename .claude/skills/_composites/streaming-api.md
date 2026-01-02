---
name: streaming-api
description: Real-time streaming with SSE, WebSocket, and LLM patterns
version: 1.0.0
tags: [streaming, sse, websocket, real-time, llm]
size: composite
atomics:
  - frontend/streaming-sse
  - frontend/streaming-websocket
  - frontend/streaming-llm
  - frontend/async-generator-cleanup
---

# Streaming API Composite

Complete streaming patterns for real-time applications.

## When to Use

- Streaming LLM responses (ChatGPT-style)
- Real-time notifications
- Live data feeds
- Chat applications
- Progress updates

## Atomic Skills

### 1. SSE (`streaming-sse`)
Server-to-client streaming, reconnection, keepalive.

### 2. WebSocket (`streaming-websocket`)
Bidirectional real-time, heartbeat, broadcasting.

### 3. LLM Streaming (`streaming-llm`)
OpenAI streaming, token-by-token rendering.

### 4. Async Generator Cleanup (`async-generator-cleanup`)
Python aclosing() for resource cleanup.

## Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│  STREAMING DECISION TREE                                    │
├─────────────────────────────────────────────────────────────┤
│  Server → Client only? ──► SSE                              │
│  Bidirectional? ──► WebSocket                               │
│  LLM responses? ──► SSE + LLM pattern                       │
│                                                             │
│  Python async generators? ──► Always use aclosing()         │
└─────────────────────────────────────────────────────────────┘
```

## Load Order

1. `streaming-sse` - Basic server-to-client
2. `streaming-websocket` - When bidirectional needed
3. `streaming-llm` - For AI chat interfaces
4. `async-generator-cleanup` - Python resource safety
