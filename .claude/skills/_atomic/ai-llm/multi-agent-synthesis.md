---
name: multi-agent-synthesis
description: Combine outputs from multiple agents into coherent results
version: 1.0.0
tags: [ai, llm, multi-agent, synthesis, llm-as-judge, voting]
size: atomic
domain: ai-llm
---

# Multi-Agent Synthesis

## Fan-Out/Fan-In Pattern

```python
async def fan_out_fan_in(task: str, agents: list[Agent]) -> str:
    """Run agents in parallel, synthesize results."""

    # Fan-out: Run all agents concurrently
    results = await asyncio.gather(
        *[agent.run(task) for agent in agents],
        return_exceptions=True
    )

    # Filter successful results
    successful = [
        {"agent": agents[i].name, "output": r}
        for i, r in enumerate(results)
        if not isinstance(r, Exception)
    ]

    # Fan-in: Synthesize
    return await synthesize(task, successful)

async def synthesize(task: str, agent_outputs: list[dict]) -> str:
    """Combine agent outputs into coherent answer."""
    results_str = "\n\n".join(
        f"**{o['agent']}**:\n{o['output']}"
        for o in agent_outputs
    )

    response = await openai.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[{
            "role": "system",
            "content": "Synthesize these agent outputs into a coherent, comprehensive answer."
        }, {
            "role": "user",
            "content": f"Task: {task}\n\nAgent Outputs:\n{results_str}"
        }]
    )
    return response.choices[0].message.content
```

## LLM-as-Judge Evaluation

```python
from pydantic import BaseModel, Field

class AgentScore(BaseModel):
    agent: str
    score: float = Field(ge=0, le=10)
    reasoning: str

class JudgementResult(BaseModel):
    rankings: list[AgentScore]
    best_answer: str
    synthesis: str

async def llm_as_judge(task: str, outputs: list[dict]) -> JudgementResult:
    """Use LLM to evaluate and rank agent outputs."""

    outputs_str = "\n\n".join(
        f"[{o['agent']}]: {o['output']}"
        for o in outputs
    )

    response = await openai.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[{
            "role": "system",
            "content": """Evaluate agent outputs on:
1. Accuracy (0-10)
2. Completeness (0-10)
3. Clarity (0-10)

Provide rankings and synthesize the best answer."""
        }, {
            "role": "user",
            "content": f"Task: {task}\n\nOutputs:\n{outputs_str}"
        }],
        response_format: { "type": "json_object" }
    )

    return JudgementResult.parse_raw(response.choices[0].message.content)
```

## Confidence-Weighted Synthesis

```python
async def confidence_weighted_synthesis(
    outputs: list[dict[str, any]]
) -> str:
    """Weight agent outputs by their confidence scores."""

    # Each output has: agent, output, confidence (0-1)
    total_confidence = sum(o["confidence"] for o in outputs)

    weighted_prompt = "\n\n".join(
        f"[{o['agent']} - Weight: {o['confidence']/total_confidence:.1%}]:\n{o['output']}"
        for o in sorted(outputs, key=lambda x: -x["confidence"])
    )

    response = await openai.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[{
            "role": "system",
            "content": "Synthesize outputs, giving more weight to higher-confidence answers."
        }, {
            "role": "user",
            "content": weighted_prompt
        }]
    )
    return response.choices[0].message.content
```

## Conflict Resolution

```python
async def resolve_conflicts(
    task: str,
    conflicting_outputs: list[dict]
) -> dict:
    """Resolve disagreements between agents."""

    response = await openai.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[{
            "role": "system",
            "content": """Agents disagree. Analyze:
1. What they agree on
2. What they disagree on
3. Which position has stronger evidence
4. Resolution recommendation"""
        }, {
            "role": "user",
            "content": f"Task: {task}\n\nConflicting Outputs:\n{json.dumps(conflicting_outputs)}"
        }],
        response_format: { "type": "json_object" }
    )

    return json.loads(response.choices[0].message.content)
```

## Best Practices

- **Diverse agents**: Different perspectives improve synthesis
- **Confidence scores**: Track how certain each agent is
- **Structured output**: Use JSON for consistent parsing
- **Track provenance**: Note which agent contributed what
