# Workflows Directory Structure

This directory contains LangGraph workflow implementations for SkillForge's analysis and tutoring pipelines.

## Directory Organization

### `agents/` - Agent Business Logic

Contains reusable agent implementations that perform specific analysis tasks:

- **Purpose**: Business logic for specialized agents (tech comparison, security auditing, implementation planning, etc.)
- **Pattern**: Agents are reusable components that can be called from multiple contexts
- **Key Files**:
  - `base.py` - Base agent functionality and shared utilities
  - `tech_comparator.py` - Technology comparison agent
  - `security_auditor.py` - Security analysis agent
  - `implementation_planner.py` - Implementation planning agent
  - `schemas/` - Pydantic schemas for agent inputs/outputs
  - `validation/` - Agent output validation logic

**Example Usage**:
```python
from app.workflows.agents.base import emit_agent_progress, save_agent_finding
from app.workflows.agents.tech_comparator import run_tech_comparator

# Agent can be called directly or via LangGraph nodes
result = await run_tech_comparator(content, analysis_id)
```

### `nodes/` - LangGraph Node Wrappers

Contains LangGraph StateGraph node implementations that integrate agents into workflows:

- **Purpose**: LangGraph integration layer that wraps agent business logic
- **Pattern**: Nodes are LangGraph-specific and handle state management, error handling, and workflow orchestration
- **Key Files**:
  - `supervisor.py` - Supervisor node that routes to agents
  - `quality_gate_node.py` - Quality validation node
  - `agents/` - Agent-specific node wrappers
    - `tech_comparator_node.py` - Wraps `agents/tech_comparator.py`
    - `security_auditor_node.py` - Wraps `agents/security_auditor.py`
    - etc.

**Example Usage**:
```python
from app.workflows.nodes.agents.tech_comparator_node import tech_comparator_node

# Node is used in LangGraph StateGraph
graph.add_node("tech_comparator", tech_comparator_node)
```

### Relationship Between Agents and Nodes

**Agents (`agents/`) = Reusable Business Logic**
- Pure functions/classes that perform analysis
- No LangGraph dependencies
- Can be tested independently
- Can be called from multiple contexts (workflows, scripts, tests)

**Nodes (`nodes/agents/`) = LangGraph Integration**
- Wrappers around agent logic
- Handle LangGraph state management
- Integrate with workflow orchestration
- Handle SSE events and progress tracking

**Pattern**:
```
agents/tech_comparator.py          # Business logic
    ↓ (called by)
nodes/agents/tech_comparator_node.py  # LangGraph wrapper
    ↓ (used in)
graph_builder.py                    # Workflow definition
```

### `tasks/` - Workflow Tasks

Contains task implementations for workflow steps:

- **Purpose**: Individual workflow steps (extraction, chunking, embedding, artifact generation)
- **Key Subdirectories**:
  - `aggregation/` - Agent findings aggregation and synthesis
  - `schemas/` - Task-specific schemas
  - `templates/` - Jinja2 templates for artifact generation

### `tutor/` - Tutoring Workflow

Separate workflow for Socratic tutoring sessions:

- **Purpose**: Self-contained tutoring workflow
- **Structure**: Mirrors main workflow structure (nodes/, tasks/, schemas/)
- **Key Features**: Multi-turn conversations, syllabus generation, readiness assessment

### `utils/` - Workflow Utilities

Shared utilities for workflows:

- Content type detection
- Import detection
- Retrieval routing
- Timeout handling

## Design Principles

1. **Separation of Concerns**: Business logic (agents) is separate from orchestration (nodes)
2. **Reusability**: Agents can be used outside of LangGraph workflows
3. **Testability**: Agents can be tested independently of LangGraph
4. **Maintainability**: Clear separation makes it easier to understand and modify code

## Adding a New Agent

1. **Create agent logic** in `agents/your_agent.py`:
   ```python
   async def run_your_agent(content: str, analysis_id: str) -> dict:
       # Agent business logic
       return {"result": "data"}
   ```

2. **Create node wrapper** in `nodes/agents/your_agent_node.py`:
   ```python
   async def your_agent_node(state: AnalysisState) -> dict:
       # Call agent logic
       result = await run_your_agent(state["content"], state["analysis_id"])
       # Handle state updates, SSE events, etc.
       return {"your_agent_result": result}
   ```

3. **Add to workflow** in `graph_builder.py`:
   ```python
   graph.add_node("your_agent", your_agent_node)
   ```

## Testing

- **Agent tests**: Test `agents/` logic independently
- **Node tests**: Test `nodes/` integration with mock state
- **Workflow tests**: Test full workflow integration

