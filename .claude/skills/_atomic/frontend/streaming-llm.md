---
name: streaming-llm
description: LLM streaming pattern for ChatGPT-style interfaces
version: 1.0.0
tags: [streaming, llm, openai, chat]
size: atomic
domain: frontend
---

# LLM Streaming

## Server (OpenAI)

```typescript
import OpenAI from 'openai'

const openai = new OpenAI()

export async function POST(req: Request) {
  const { messages } = await req.json()

  const stream = await openai.chat.completions.create({
    model: 'gpt-4-turbo-preview',
    messages,
    stream: true
  })

  const encoder = new TextEncoder()

  return new Response(
    new ReadableStream({
      async start(controller) {
        for await (const chunk of stream) {
          const content = chunk.choices[0]?.delta?.content
          if (content) {
            controller.enqueue(
              encoder.encode(`data: ${JSON.stringify({ content })}\n\n`)
            )
          }
        }
        controller.enqueue(encoder.encode('data: [DONE]\n\n'))
        controller.close()
      }
    }),
    {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache'
      }
    }
  )
}
```

## Client

```typescript
async function streamChat(messages: Message[]) {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages })
  })

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const chunk = decoder.decode(value)
    const lines = chunk.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6)
        if (data === '[DONE]') return

        const { content } = JSON.parse(data)
        appendToUI(content)  // Stream token to UI
      }
    }
  }
}
```

## React Component

```tsx
function ChatMessage({ messagePromise }) {
  const [content, setContent] = useState('')

  useEffect(() => {
    let cancelled = false

    async function stream() {
      for await (const token of streamChat(messagePromise)) {
        if (cancelled) break
        setContent(prev => prev + token)
      }
    }

    stream()
    return () => { cancelled = true }
  }, [messagePromise])

  return <div className="message">{content}</div>
}
```

## Best Practices

- ✅ Show typing indicator while streaming
- ✅ Handle [DONE] signal for completion
- ✅ Allow user to cancel generation
- ✅ Buffer partial JSON for robustness
