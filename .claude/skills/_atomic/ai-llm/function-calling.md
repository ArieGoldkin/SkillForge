---
name: function-calling
description: Enable LLMs to use external tools and APIs
version: 1.0.0
tags: [ai, llm, function-calling, tools, openai, anthropic]
size: atomic
domain: ai-llm
---

# Function Calling

## Tool Definition (OpenAI)

```typescript
const tools = [{
  type: 'function',
  function: {
    name: 'get_weather',
    description: 'Get current weather for a location',
    parameters: {
      type: 'object',
      properties: {
        location: { type: 'string', description: 'City and state, e.g., San Francisco, CA' },
        unit: { type: 'string', enum: ['celsius', 'fahrenheit'] }
      },
      required: ['location']
    }
  }
}]
```

## Function Calling Loop

```typescript
async function chatWithTools(userMessage: string) {
  const messages = [{ role: 'user', content: userMessage }]

  while (true) {
    const response = await openai.chat.completions.create({
      model: 'gpt-4-turbo-preview',
      messages,
      tools
    })

    const message = response.choices[0].message

    // No tool calls - return final answer
    if (!message.tool_calls) return message.content

    // Execute tool calls
    messages.push(message)
    for (const toolCall of message.tool_calls) {
      const result = await executeFunction(
        toolCall.function.name,
        JSON.parse(toolCall.function.arguments)
      )
      messages.push({
        role: 'tool',
        tool_call_id: toolCall.id,
        content: JSON.stringify(result)
      })
    }
  }
}
```

## Claude Tool Calling

```typescript
import Anthropic from '@anthropic-ai/sdk'

const claudeTools = [{
  name: 'get_weather',
  description: 'Get current weather',
  input_schema: {
    type: 'object',
    properties: { location: { type: 'string' } },
    required: ['location']
  }
}]

async function claudeWithTools(userMessage: string) {
  const messages = [{ role: 'user', content: userMessage }]

  while (true) {
    const response = await anthropic.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 1024,
      tools: claudeTools,
      messages
    })

    const toolUse = response.content.find(b => b.type === 'tool_use')
    if (!toolUse) {
      return response.content.find(b => b.type === 'text')?.text || ''
    }

    const result = await executeFunction(toolUse.name, toolUse.input)
    messages.push(
      { role: 'assistant', content: response.content },
      { role: 'user', content: [{ type: 'tool_result', tool_use_id: toolUse.id, content: JSON.stringify(result) }] }
    )
  }
}
```

## Input Validation with Zod

```typescript
import { z } from 'zod'

const schemas = {
  get_weather: z.object({
    location: z.string().min(1),
    unit: z.enum(['celsius', 'fahrenheit']).default('fahrenheit')
  })
}

async function executeWithValidation(name: string, args: any) {
  const validated = schemas[name].parse(args)
  return await registry.execute(name, validated)
}
```

## Best Practices

- **Clear descriptions**: Be specific about what the tool does and expects
- **Limit tools**: 10-20 max to avoid confusion
- **Validate inputs**: Use Zod or similar before execution
- **Handle errors**: Return structured errors for LLM to handle
