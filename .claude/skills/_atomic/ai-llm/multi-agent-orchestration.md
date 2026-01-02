---
name: multi-agent-orchestration
description: Coordinate multiple specialized AI agents for complex tasks
version: 1.0.0
tags: [ai, llm, multi-agent, orchestration, supervisor, coordination]
size: atomic
domain: ai-llm
---

# Multi-Agent Orchestration

## Supervisor Pattern

```typescript
interface Agent {
  name: string
  role: string
  tools: string[]
  systemPrompt: string
}

class AgentCoordinator {
  private agents: Map<string, Agent>

  async executeTask(task: string): Promise<string> {
    // 1. Plan: Decompose task and assign agents
    const plan = await this.createPlan(task)

    // 2. Execute: Run agents in sequence or parallel
    const results = new Map<string, any>()
    for (const step of plan.steps) {
      if (step.parallel) {
        const parallelResults = await Promise.all(
          step.agents.map(name => this.runAgent(name, step.task, results))
        )
        parallelResults.forEach((result, i) => results.set(step.agents[i], result))
      } else {
        for (const agentName of step.agents) {
          results.set(agentName, await this.runAgent(agentName, step.task, results))
        }
      }
    }

    // 3. Synthesize results
    return this.synthesizeResults(task, results)
  }

  private async createPlan(task: string) {
    const response = await openai.chat.completions.create({
      model: 'gpt-4-turbo-preview',
      messages: [{
        role: 'system',
        content: `Create execution plan. Available agents: ${this.getAgentDescriptions()}
Return JSON: { steps: [{ agents: string[], task: string, parallel: boolean }] }`
      }, { role: 'user', content: task }],
      response_format: { type: 'json_object' }
    })
    return JSON.parse(response.choices[0].message.content!)
  }
}
```

## Opus 4.5 Orchestrator

Use extended thinking for complex orchestration:

```python
from anthropic import Anthropic

client = Anthropic()

async def orchestrate_with_extended_thinking(task: str, agents: list[Agent]) -> dict:
    """Use Claude Opus 4.5 extended thinking for orchestration."""

    agent_specs = "\n".join(f"- {a.name}: {a.role}" for a in agents)

    response = client.messages.create(
        model="claude-opus-4-5-20250514",
        max_tokens=16000,
        thinking={
            "type": "enabled",
            "budget_tokens": 10000  # Deep reasoning budget
        },
        messages=[{
            "role": "user",
            "content": f"""Analyze this task and create optimal agent execution plan.

Task: {task}

Available Agents:
{agent_specs}

Consider:
1. Dependencies between agents
2. Which can run in parallel
3. How to handle conflicts
4. Optimal execution order"""
        }]
    )

    return {
        "thinking": response.content[0].thinking if hasattr(response.content[0], 'thinking') else None,
        "plan": response.content[-1].text
    }
```

## Dependency Graph Execution

```python
from dataclasses import dataclass
import asyncio

@dataclass
class AgentTask:
    agent: str
    task: str
    dependencies: list[str] = None

async def execute_with_dependencies(tasks: list[AgentTask]) -> dict:
    """Execute agents respecting dependencies."""
    results = {}
    completed = set()

    while len(completed) < len(tasks):
        # Find tasks whose dependencies are met
        ready = [
            t for t in tasks
            if t.agent not in completed
            and all(dep in completed for dep in (t.dependencies or []))
        ]

        # Execute ready tasks in parallel
        coros = [run_agent(t.agent, t.task, results) for t in ready]
        batch_results = await asyncio.gather(*coros)

        for task, result in zip(ready, batch_results):
            results[task.agent] = result
            completed.add(task.agent)

    return results
```

## Best Practices

- **Limit agents**: 5-10 max for most tasks
- **Clear roles**: Each agent has distinct responsibility
- **Parallel when possible**: Reduce latency with concurrent execution
- **Conflict resolution**: Define how to handle disagreements
- **Observability**: Log each agent's input/output for debugging
