---
name: streaming-responses
description: Stream LLM responses in real-time for better UX
version: 1.0.0
tags: [ai, llm, streaming, sse, realtime, backpressure]
size: atomic
domain: ai-llm
---

# Streaming Responses

## OpenAI Streaming

```typescript
async function* streamResponse(prompt: string) {
  const stream = await openai.chat.completions.create({
    model: 'gpt-4-turbo-preview',
    messages: [{ role: 'user', content: prompt }],
    stream: true
  })

  for await (const chunk of stream) {
    const content = chunk.choices[0]?.delta?.content
    if (content) yield content
  }
}

// Usage
for await (const chunk of streamResponse("Write a poem")) {
  process.stdout.write(chunk)
}
```

## Anthropic Claude Streaming

```python
from anthropic import Anthropic

client = Anthropic()

async def stream_claude(prompt: str):
    with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for text in stream.text_stream:
            yield text
```

## Server-Sent Events (SSE) for Web

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/stream")
async def stream_endpoint(prompt: str):
    async def generate():
        async for chunk in stream_llm(prompt):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
```

## Frontend SSE Consumer

```typescript
async function consumeStream(prompt: string, onChunk: (text: string) => void) {
  const response = await fetch(`/stream?prompt=${encodeURIComponent(prompt)}`)
  const reader = response.body!.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const text = decoder.decode(value)
    const lines = text.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6)
        if (data === '[DONE]') return
        onChunk(JSON.parse(data).content)
      }
    }
  }
}

// React hook
function useStream(prompt: string) {
  const [text, setText] = useState('')

  useEffect(() => {
    consumeStream(prompt, chunk => setText(prev => prev + chunk))
  }, [prompt])

  return text
}
```

## Streaming with Tool Calls

```typescript
async function* streamWithTools(prompt: string) {
  const stream = await openai.chat.completions.create({
    model: 'gpt-4-turbo-preview',
    messages: [{ role: 'user', content: prompt }],
    tools,
    stream: true
  })

  let currentToolCall: any = null

  for await (const chunk of stream) {
    const delta = chunk.choices[0]?.delta

    // Tool call accumulation
    if (delta.tool_calls) {
      const tc = delta.tool_calls[0]
      if (tc.function?.name) {
        currentToolCall = { id: tc.id, name: tc.function.name, arguments: '' }
      }
      if (tc.function?.arguments) {
        currentToolCall.arguments += tc.function.arguments
      }
    }

    // Regular content
    if (delta.content) yield { type: 'content', text: delta.content }
  }

  // Execute tool if present
  if (currentToolCall) {
    const result = await executeFunction(
      currentToolCall.name,
      JSON.parse(currentToolCall.arguments)
    )
    yield { type: 'tool_result', tool: currentToolCall.name, result }
  }
}
```

## Backpressure Handling

```python
import asyncio

async def stream_with_backpressure(prompt: str, buffer_size: int = 100):
    """Handle slow consumers with bounded buffer."""
    queue = asyncio.Queue(maxsize=buffer_size)

    async def producer():
        async for chunk in stream_llm(prompt):
            await queue.put(chunk)  # Blocks if buffer full
        await queue.put(None)  # Signal completion

    async def consumer():
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk

    asyncio.create_task(producer())
    async for chunk in consumer():
        yield chunk
```

## Best Practices

- **Disable buffering**: Set headers to prevent nginx/proxy buffering
- **Heartbeats**: Send periodic keep-alive for long generations
- **Error handling**: Send error events, not just cut off
- **Backpressure**: Use bounded buffers for slow consumers
