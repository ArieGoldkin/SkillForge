---
name: agentic-workflows
description: LLM agents that reason, plan, and take autonomous actions
version: 1.0.0
tags: [ai, llm, agents, react, tree-of-thoughts, autonomous]
size: atomic
domain: ai-llm
---

# Agentic Workflows

## ReAct Pattern (Reasoning + Acting)

```typescript
async function reactAgent(task: string) {
  const messages = [{
    role: 'system',
    content: `Use this format:
Thought: [reasoning about what to do next]
Action: [tool name]
Action Input: [parameters as JSON]
Observation: [tool result]
... (repeat as needed)
Answer: [final answer]`
  }, { role: 'user', content: task }]

  const maxIterations = 10
  let iteration = 0

  while (iteration < maxIterations) {
    const response = await openai.chat.completions.create({
      model: 'gpt-4-turbo-preview',
      messages
    })

    const content = response.choices[0].message.content!

    // Final answer reached
    if (content.includes('Answer:')) {
      return content.split('Answer:')[1].trim()
    }

    // Extract and execute action
    const actionMatch = content.match(/Action: (.*?)\n/)
    const inputMatch = content.match(/Action Input: (.*?)\n/)

    if (actionMatch && inputMatch) {
      const result = await executeTool(actionMatch[1].trim(), JSON.parse(inputMatch[1]))
      messages.push({ role: 'assistant', content })
      messages.push({ role: 'user', content: `Observation: ${JSON.stringify(result)}` })
    }

    iteration++
  }

  throw new Error('Agent exceeded max iterations')
}
```

## Tree of Thoughts

Explore multiple reasoning paths before committing:

```typescript
async function treeOfThoughts(problem: string, depth = 3) {
  async function generateThoughts(context: string): Promise<string[]> {
    const response = await openai.chat.completions.create({
      model: 'gpt-4-turbo-preview',
      messages: [{
        role: 'system',
        content: 'Generate 3 different approaches to solve this problem.'
      }, { role: 'user', content: context }]
    })
    return response.choices[0].message.content!.split('\n').filter(t => t.trim())
  }

  async function evaluateThought(thought: string): Promise<number> {
    const response = await openai.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages: [{
        role: 'system',
        content: 'Rate this solution approach from 0-10.'
      }, { role: 'user', content: thought }]
    })
    return parseFloat(response.choices[0].message.content || '5')
  }

  // Build tree, score thoughts, find best path
  // ...implementation
}
```

## Self-Correction Pattern

```python
async def run_with_self_correction(
    agent: Agent,
    input_messages: list[dict],
    validator: Validator,
    max_retries: int = 2,
) -> dict:
    """Execute agent with self-correction loop."""
    current_messages = input_messages

    for attempt in range(max_retries + 1):
        output = await agent.invoke(current_messages)
        validation = validator.validate(output)

        if validation.is_valid:
            return output  # Success!

        if not validation.retry_recommended or attempt >= max_retries:
            break  # Accept degraded output

        # Build correction prompt
        current_messages = [
            *input_messages,
            {"role": "assistant", "content": str(output)},
            {"role": "user", "content": f"Issues: {validation.issues}. Please fix."},
        ]

    return output
```

## Best Practices

- **Max iterations**: Limit to 10-20 to prevent runaway loops
- **Error recovery**: Catch tool failures gracefully
- **Safety guards**: Validate inputs/outputs with moderation API
- **Model selection**: Use GPT-4 for complex reasoning, GPT-3.5 for simple actions
