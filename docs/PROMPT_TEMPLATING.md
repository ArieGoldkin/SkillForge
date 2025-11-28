# Prompt Templating Guide

**Version:** 1.0  
**Last Updated:** November 28, 2025  
**Status:** ✅ Implemented & Tested

---

## Overview

SkillForge uses a hybrid templating approach following LangGraph best practices:
- **f-strings** for simple, static prompts (slot-fill scenarios)
- **Jinja2** for complex prompts requiring loops, conditionals, or structured iteration

This guide shows where the new templating infrastructure lives and how to use it.

---

## 📁 Folder Structure (ASCII Art)

```
backend/
├── app/
│   ├── core/
│   │   └── template_utils.py          ⭐ NEW: Jinja2 rendering utilities
│   │
│   └── workflows/
│       ├── agents/
│       │   ├── prompt_builders.py     ⭐ NEW: Agent prompt builders
│       │   │   ├── build_agent_user_prompt()
│       │   │   └── build_supervisor_user_prompt()
│       │   │
│       │   └── execution.py           ✏️  UPDATED: Uses prompt_builders
│       │
│       ├── nodes/
│       │   └── supervisor.py          ✏️  UPDATED: Uses prompt_builders
│       │
│       └── tasks/
│           ├── prompt_builders.py      ⭐ NEW: Task prompt builders
│           │   └── build_synthesis_user_prompt()
│           │
│           ├── templates/              ⭐ NEW: Jinja2 templates directory
│           │   └── aggregation_findings.j2  ⭐ NEW: Findings template
│           │
│           ├── aggregation_helpers.py ✏️  UPDATED: Uses Jinja2 template
│           └── aggregate_findings.py  ✏️  UPDATED: Uses prompt_builders
│
└── tests/
    └── unit/
        └── workflows/
            ├── agents/
            │   └── test_prompt_builders.py      ⭐ NEW: 8 tests
            └── tasks/
                ├── test_prompt_builders.py       ⭐ NEW: 4 tests
                └── test_aggregation_templates.py  ⭐ NEW: 8 tests
```

**Legend:**
- ⭐ NEW = Newly added files
- ✏️ UPDATED = Existing files modified to use new infrastructure

---

## 🚀 Usage Guide

### 1. Using Prompt Builders (f-strings)

Prompt builders are pure functions for constructing simple prompts. Use them for "slot-fill" scenarios.

#### For Agent Analysis

```python
from app.workflows.agents.prompt_builders import build_agent_user_prompt

# Build prompt for agent analysis
user_prompt = build_agent_user_prompt(
    content="Full article text here...",
    content_type="article",
    max_length=1500,  # Optional, defaults to 1500
)

# Result:
# "Content Type: article
#
# Content:
# Full article text here..."
```

#### For Supervisor Routing

```python
from app.workflows.agents.prompt_builders import build_supervisor_user_prompt

# Build prompt for supervisor
user_prompt = build_supervisor_user_prompt(
    system_prompt=SUPERVISOR_PROMPT,
    content=sized_content,
    content_type="article",
)
```

#### For Synthesis

```python
from app.workflows.tasks.prompt_builders import build_synthesis_user_prompt

# Build prompt for LLM synthesis
formatted_findings = format_findings_for_llm(...)  # Returns Jinja2-rendered string
user_prompt = build_synthesis_user_prompt(formatted_findings)
```

---

### 2. Using Jinja2 Templates (for loops/conditionals)

Use Jinja2 when you need to iterate over collections or have conditional sections.

#### Rendering a Template

```python
from app.core.template_utils import render_jinja_template

# Prepare context data (precompute in Python, not in template)
context = {
    "agent_findings": [
        {
            "agent_type": "tech_comparator",
            "findings": {"primary_tech": "LangGraph", "recommendation": "Use it"},
        },
        {
            "agent_type": "security_auditor",
            "findings": {"risks": []},
        },
    ],
    "conflicts": [
        {
            "agent_1": "tech_comparator",
            "agent_2": "security_auditor",
            "conflict": "Tech recommends, security warns",
        }
    ],
    "confidence_scores": {
        "tech_comparator": 0.85,
        "security_auditor": 0.90,
    },
}

# Render template (defaults to workflows/tasks/templates/)
formatted = render_jinja_template("aggregation_findings.j2", context)
```

#### Custom Template Directory

```python
# Use custom template directory
formatted = render_jinja_template(
    "my_template.j2",
    context,
    template_dir="app/workflows/custom/templates",
)
```

---

### 3. Creating New Templates

#### Step 1: Create Template File

Create a `.j2` file in `backend/app/workflows/tasks/templates/`:

```jinja2
# my_template.j2
AGENT RESULTS:

{% for result in agent_results %}
--- {{ result.agent_name | upper }} ---
Status: {{ result.status }}
Output: {{ result.output | tojson(indent=2) }}

{% endfor %}

{% if errors %}
ERRORS:
{% for error in errors %}
- {{ error.message }} ({{ error.agent }})
{% endfor %}
{% endif %}
```

#### Step 2: Use in Code

```python
from app.core.template_utils import render_jinja_template

context = {
    "agent_results": [...],
    "errors": [...],
}

output = render_jinja_template("my_template.j2", context)
```

---

## 📋 Best Practices

### When to Use f-strings (Prompt Builders)

✅ **Use prompt builders for:**
- Simple slot-fill prompts
- Static prompts with variable substitution
- Prompts that map directly to function parameters
- Security-sensitive prompts (f-strings are safer)

**Example:**
```python
# ✅ GOOD: Simple slot-fill
prompt = build_agent_user_prompt(content, content_type)
```

### When to Use Jinja2 Templates

✅ **Use Jinja2 for:**
- Looping over collections (lists, dicts)
- Conditional sections (if/else blocks)
- Complex formatting with multiple iterations
- Reusable template structures

**Example:**
```python
# ✅ GOOD: Looping over findings
formatted = render_jinja_template("aggregation_findings.j2", {
    "agent_findings": findings_list,  # Loop in template
    "conflicts": conflicts_list,      # Conditional section
    "confidence_scores": scores_dict,  # Loop + sorting
})
```

### ❌ Anti-Patterns

```python
# ❌ BAD: Complex logic in template
# Template should only handle presentation, not business logic

# ❌ BAD: Accepting Jinja2 from untrusted sources
# Never accept template strings from user input or database

# ❌ BAD: Mixing f-strings with loops
formatted = ""
for item in items:
    formatted += f"Item: {item}\n"  # Use Jinja2 instead!
```

---

## 🧪 Testing

All prompt builders and templates have comprehensive test coverage:

### Running Tests

```bash
# Test prompt builders
poetry run pytest tests/unit/workflows/agents/test_prompt_builders.py -v
poetry run pytest tests/unit/workflows/tasks/test_prompt_builders.py -v

# Test Jinja2 templates
poetry run pytest tests/unit/workflows/tasks/test_aggregation_templates.py -v

# Test integration
poetry run pytest tests/integration/workflows/test_aggregation.py -v
```

### Test Coverage

- **Prompt Builders:** 12 tests (8 agent + 4 task)
- **Jinja2 Templates:** 8 tests
- **Integration:** 3 tests
- **Total:** 43 tests passing ✅

---

## 📚 Reference

### Available Prompt Builders

| Function | Location | Purpose |
|----------|----------|---------|
| `build_agent_user_prompt()` | `agents/prompt_builders.py` | Agent analysis prompts |
| `build_supervisor_user_prompt()` | `agents/prompt_builders.py` | Supervisor routing prompts |
| `build_synthesis_user_prompt()` | `tasks/prompt_builders.py` | LLM synthesis prompts |

### Available Templates

| Template | Location | Purpose |
|----------|----------|---------|
| `aggregation_findings.j2` | `tasks/templates/` | Format agent findings for synthesis |

### Template Utilities

| Function | Location | Purpose |
|----------|----------|---------|
| `render_jinja_template()` | `core/template_utils.py` | Render Jinja2 templates with caching |

---

## 🔄 Migration Guide

If you have existing code using inline f-strings with loops:

### Before (String Concatenation)

```python
def format_results(results: list[dict]) -> str:
    formatted = "RESULTS:\n\n"
    for result in results:
        formatted += f"--- {result['name']} ---\n"
        formatted += f"Status: {result['status']}\n\n"
    return formatted
```

### After (Jinja2 Template)

**1. Create template (`results.j2`):**
```jinja2
RESULTS:

{% for result in results %}
--- {{ result.name }} ---
Status: {{ result.status }}

{% endfor %}
```

**2. Update code:**
```python
from app.core.template_utils import render_jinja_template

def format_results(results: list[dict]) -> str:
    return render_jinja_template("results.j2", {"results": results})
```

---

## 🎯 Summary

- ✅ **f-strings** for simple prompts → Use `prompt_builders.py`
- ✅ **Jinja2** for loops/conditionals → Use `template_utils.py` + `.j2` templates
- ✅ All functions are **pure** and **testable**
- ✅ Templates are **cached** for performance
- ✅ Follows **LangGraph best practices**

For questions or issues, see the test files for usage examples.
