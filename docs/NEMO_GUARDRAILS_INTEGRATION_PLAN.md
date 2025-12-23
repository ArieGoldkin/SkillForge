# 🛡️ NVIDIA NeMo Guardrails Integration Plan for SkillForge

**Research Date:** December 22, 2025  
**Status:** Research Complete - Ready for Implementation  
**Priority:** High (Security & Quality Enhancement)

---

## 📋 Executive Summary

**NeMo Guardrails** is an open-source toolkit from NVIDIA that enables programmable guardrails for LLM-based applications. This document outlines a comprehensive integration plan to add safety, security, and quality controls to SkillForge's LangGraph workflows.

### Key Benefits

1. **Security**: Prevent jailbreak attacks, malicious prompts, and PII leakage
2. **Quality**: Ensure agents stay on-topic (technical learning), filter inappropriate responses
3. **Compliance**: Add audit trail for safety violations
4. **User Trust**: Safe, controlled LLM interactions
5. **Cost Savings**: Block malicious requests before expensive LLM calls

### Integration Points

- **Analysis Workflow**: 8 specialized agents (Tech Comparator, Security Auditor, etc.)
- **Tutor Workflow**: Socratic questioning and lesson delivery
- **API Endpoints**: User input validation before workflow execution

---

## 🔍 Research Findings

### 1. NeMo Guardrails Capabilities

#### Core Features
- **Input Rails**: Validate and filter user input (jailbreak detection, malicious content)
- **Output Rails**: Filter LLM responses (inappropriate content, PII leakage)
- **Topical Rails**: Keep conversations on specific topics
- **Dialog Rails**: Control conversation flow and enforce SOPs
- **Tool/Action Rails**: Secure connections to external services

#### LangGraph Integration Pattern

```python
from nemoguardrails import RailsConfig
from nemoguardrails.integrations.langchain.runnable_rails import RunnableRails

# Load configuration
config = RailsConfig.from_path("config.yml")
guardrails = RunnableRails(config=config, passthrough=True, verbose=True)

# Wrap LLM with guardrails
runnable_with_guardrails = prompt | (guardrails | llm)
```

**Key Pattern**: `prompt | (guardrails | llm)` - Guardrails sit between prompt and LLM, intercepting both input and output.

### 2. SkillForge Architecture Analysis

#### Current State
- ✅ **Pydantic validation** for API inputs (basic type checking)
- ✅ **Quality gates** for output validation (LLM-as-judge)
- ❌ **No input guardrails** (jailbreak detection, malicious prompts)
- ❌ **No output filtering** (inappropriate content, PII)
- ❌ **No topical control** (ensuring technical focus)

#### Workflow Structure

```
Analysis Workflow:
  extract → embedding → [chunk_and_embed, inject_context, supervisor] (parallel)
    → [8 agent nodes] (parallel via Send API)
    → aggregate → quality_gate → generate_artifact

Tutor Workflow:
  generate_syllabus → deliver_lesson → ask_socratic → assess_readiness
    → [rephrase_explain | conduct_review | final_challenge]
```

#### Agent Architecture

All agents use `create_structured_agent()` from `backend/app/domains/analysis/workflows/agents/base.py`:
- Uses `get_chat_model()` from `backend/app/core/model_factory.py`
- Supports structured output via ToolStrategy
- Has tracing via `robust_traceable` decorator

**Integration Point**: Wrap LLM in `model_factory.py` or agent `base.py` to apply guardrails automatically.

### 3. GitHub Issues Analysis

**Relevant Issues:**
- #442: Quality gate fail-open allows low-quality artifacts (output validation concern)
- #455: Low specificity research content (topical control needed)
- #454: G-Eval depth=0.0 for empty/failed agent outputs (output validation)

**No existing security/jailbreak issues**, but proactive guardrails would prevent future problems.

---

## 🎯 Integration Strategy

### Architecture Decision

**Guardrails at Agent Level** (not workflow level):
- ✅ Each agent has different safety requirements (security_auditor vs tutor)
- ✅ Granular control per agent type
- ✅ Reuse guardrails config across similar agents
- ✅ Minimal code changes (wrap in `base.py` or `model_factory.py`)

### Implementation Approach

1. **Create Guardrails Service Module**
   - Location: `backend/app/shared/services/guardrails/`
   - Components:
     - `config_loader.py`: Load Colang 2.0 configs
     - `rails_wrapper.py`: RunnableRails wrapper
     - `monitoring.py`: Log violations, metrics

2. **Modify Model Factory**
   - Location: `backend/app/core/model_factory.py`
   - Add optional guardrails wrapping based on:
     - Feature flag: `ENABLE_GUARDRAILS`
     - Domain: `analysis` vs `tutor`
     - Task type: `agent` vs `supervisor` vs `g_eval`

3. **Create Colang 2.0 Config Files**
   - Location: `backend/config/guardrails/`
   - Files:
     - `base.co`: Shared safety rules (jailbreak detection, PII)
     - `analysis.co`: Analysis workflow rails (input/output, topical)
     - `tutor.co`: Tutor workflow rails (dialog, topical)

4. **Add Feature Flag**
   - Location: `backend/app/core/config.py`
   - Setting: `ENABLE_GUARDRAILS: bool = False` (default: disabled for gradual rollout)

---

## 📐 Architecture Diagram

```mermaid
graph TB
    subgraph "API Layer"
        API[FastAPI Endpoints]
        UserInput[User Input]
    end
    
    subgraph "Guardrails Layer (NEW)"
        InputRails[Input Rails<br/>Jailbreak Detection<br/>Malicious Content]
        OutputRails[Output Rails<br/>Content Filtering<br/>PII Detection]
        TopicalRails[Topical Rails<br/>Technical Focus<br/>Topic Control]
    end
    
    subgraph "Workflow Layer"
        AnalysisWF[Analysis Workflow]
        TutorWF[Tutor Workflow]
    end
    
    subgraph "Agent Layer"
        Agent1[Tech Comparator]
        Agent2[Security Auditor]
        Agent3[Implementation Planner]
        Agent4[Performance Analyst]
        Agent5[Code Quality Critic]
        Agent6[Trend Validator]
        Agent7[Dependency Mapper]
        Agent8[Integration Feasibility]
        TutorAgent[Tutor Agent]
    end
    
    subgraph "LLM Layer"
        LLM[Chat Model<br/>Claude/GPT/Gemini]
    end
    
    UserInput --> API
    API --> InputRails
    InputRails --> AnalysisWF
    InputRails --> TutorWF
    
    AnalysisWF --> Agent1
    AnalysisWF --> Agent2
    AnalysisWF --> Agent3
    AnalysisWF --> Agent4
    AnalysisWF --> Agent5
    AnalysisWF --> Agent6
    AnalysisWF --> Agent7
    AnalysisWF --> Agent8
    
    TutorWF --> TutorAgent
    
    Agent1 --> OutputRails
    Agent2 --> OutputRails
    Agent3 --> OutputRails
    Agent4 --> OutputRails
    Agent5 --> OutputRails
    Agent6 --> OutputRails
    Agent7 --> OutputRails
    Agent8 --> OutputRails
    TutorAgent --> OutputRails
    
    OutputRails --> TopicalRails
    TopicalRails --> LLM
    
    style InputRails fill:#ff6b6b,color:#fff
    style OutputRails fill:#ff6b6b,color:#fff
    style TopicalRails fill:#ff6b6b,color:#fff
```

---

## 🚀 Implementation Plan

### Phase 1: MVP - Analysis Workflow Guardrails (Week 1-2)

**Goal**: Add input/output rails to analysis workflow agents

#### Tasks

1. **Setup NeMo Guardrails**
   ```bash
   cd backend
   poetry add nemoguardrails
   ```

2. **Create Guardrails Service**
   - `backend/app/shared/services/guardrails/__init__.py`
   - `backend/app/shared/services/guardrails/config_loader.py`
   - `backend/app/shared/services/guardrails/rails_wrapper.py`

3. **Create Base Config**
   - `backend/config/guardrails/base.co`:
     ```colang
     define user ask about technical topics
     define bot respond with technical guidance
     
     define flow input guardrails
       user "jailbreak attempt detected"
       bot "I can only help with technical learning topics."
     ```

4. **Create Analysis Config**
   - `backend/config/guardrails/analysis.co`:
     ```colang
     include base.co
     
     define flow topical rails
       user asks about non-technical topics
       bot "I focus on technical learning. Let's discuss implementation guides."
     ```

5. **Modify Model Factory**
   - Add guardrails wrapping in `get_chat_model()` when `ENABLE_GUARDRAILS=True` and `task_type="agent"`

6. **Add Feature Flag**
   - `ENABLE_GUARDRAILS: bool = False` in `config.py`

7. **Add Tests**
   - `backend/tests/unit/services/guardrails/test_rails_wrapper.py`
   - Test jailbreak detection, output filtering

#### Success Criteria
- ✅ Guardrails block jailbreak attempts
- ✅ Guardrails filter inappropriate agent outputs
- ✅ No performance degradation (<300ms latency)
- ✅ Tests pass with 80%+ coverage

---

### Phase 2: Tutor Workflow Guardrails (Week 3)

**Goal**: Add dialog rails to tutor workflow

#### Tasks

1. **Create Tutor Config**
   - `backend/config/guardrails/tutor.co`:
     ```colang
     include base.co
     
     define flow dialog rails
       user asks off-topic question
       bot "Let's focus on the lesson. Here's a Socratic question..."
     ```

2. **Modify Tutor Workflow**
   - Apply guardrails to `ask_socratic`, `deliver_lesson` nodes

3. **Add Tests**
   - Test dialog flow control
   - Test topical enforcement

#### Success Criteria
- ✅ Tutor stays on-topic during lessons
- ✅ Dialog rails enforce Socratic questioning flow
- ✅ No disruption to learning experience

---

### Phase 3: Advanced Features (Week 4-5)

**Goal**: Add advanced guardrails (topical rails, tool security)

#### Tasks

1. **Enhanced Topical Rails**
   - Fine-tune technical topic detection
   - Add domain-specific rules (RAG, LangGraph, API design, etc.)

2. **Tool/Action Security**
   - Guard external service connections
   - Validate tool inputs/outputs

3. **Monitoring Dashboard**
   - Log guardrail violations
   - Metrics: violation rate, blocked requests, false positives

4. **Configuration Management**
   - Environment-specific configs (dev/staging/prod)
   - A/B testing framework for guardrail tuning

#### Success Criteria
- ✅ Advanced topical control working
- ✅ Tool security implemented
- ✅ Monitoring dashboard operational
- ✅ Config management in place

---

## 📝 Code Examples

### 1. Guardrails Service Module

```python
# backend/app/shared/services/guardrails/config_loader.py
from pathlib import Path
from nemoguardrails import RailsConfig
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

def load_guardrails_config(domain: str = "analysis") -> RailsConfig | None:
    """Load NeMo Guardrails configuration for a domain.
    
    Args:
        domain: Domain name ("analysis" or "tutor")
    
    Returns:
        RailsConfig instance or None if guardrails disabled
    """
    if not settings.ENABLE_GUARDRAILS:
        return None
    
    config_dir = Path(__file__).parent.parent.parent.parent / "config" / "guardrails"
    config_file = config_dir / f"{domain}.co"
    
    if not config_file.exists():
        logger.warning(
            "guardrails_config_not_found",
            domain=domain,
            config_file=str(config_file),
        )
        return None
    
    try:
        config = RailsConfig.from_path(str(config_dir))
        logger.info(
            "guardrails_config_loaded",
            domain=domain,
            config_file=str(config_file),
        )
        return config
    except Exception as e:
        logger.error(
            "guardrails_config_load_failed",
            domain=domain,
            error=str(e),
        )
        return None
```

```python
# backend/app/shared/services/guardrails/rails_wrapper.py
from typing import TYPE_CHECKING
from nemoguardrails import RailsConfig
from nemoguardrails.integrations.langchain.runnable_rails import RunnableRails
from langchain_core.runnables import Runnable
from app.core.logging import get_logger

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

logger = get_logger(__name__)

def wrap_with_guardrails(
    llm: "BaseChatModel",
    config: RailsConfig | None,
    passthrough: bool = True,
) -> Runnable:
    """Wrap LLM with NeMo Guardrails.
    
    Args:
        llm: Chat model to wrap
        config: Guardrails configuration (None = no guardrails)
        passthrough: Enable passthrough mode for tool calling
    
    Returns:
        Runnable with guardrails applied, or original LLM if config is None
    """
    if config is None:
        return llm
    
    try:
        guardrails = RunnableRails(
            config=config,
            passthrough=passthrough,
            verbose=settings.LOG_LEVEL == "DEBUG",
        )
        logger.info("guardrails_wrapper_created", passthrough=passthrough)
        return guardrails | llm
    except Exception as e:
        logger.error(
            "guardrails_wrapper_failed",
            error=str(e),
            fallback="no_guardrails",
        )
        return llm
```

### 2. Model Factory Integration

```python
# backend/app/core/model_factory.py (modifications)
from app.shared.services.guardrails.config_loader import load_guardrails_config
from app.shared.services.guardrails.rails_wrapper import wrap_with_guardrails

def get_chat_model(
    config: dict[str, dict[str, object]] | None = None,
    task_type: str | None = None,
    domain: str = "analysis",  # NEW: domain parameter
) -> BaseChatModel:
    """Create a chat model instance with optional guardrails.
    
    Args:
        config: Optional runtime config dict
        task_type: Optional task type for model routing
        domain: Domain name ("analysis" or "tutor") for guardrails config
    
    Returns:
        Configured chat model with guardrails applied if enabled
    """
    # ... existing model initialization code ...
    
    # Apply guardrails if enabled
    if settings.ENABLE_GUARDRAILS and task_type in ("agent", "synthesis", None):
        guardrails_config = load_guardrails_config(domain=domain)
        if guardrails_config:
            model = wrap_with_guardrails(
                llm=model,
                config=guardrails_config,
                passthrough=True,  # Required for tool calling
            )
            logger.info(
                "guardrails_applied",
                domain=domain,
                task_type=task_type,
            )
    
    return model
```

### 3. Colang 2.0 Configuration

```colang
# backend/config/guardrails/base.co
# Base safety rules shared across all domains

define user ask about technical topics
define bot respond with technical guidance

# Input Rails: Jailbreak Detection
define flow input guardrails
  user "jailbreak attempt detected" or user "ignore previous instructions"
  bot "I can only help with technical learning topics. How can I assist with implementation guides?"

# Output Rails: Content Filtering
define flow output guardrails
  bot response contains inappropriate content
  bot "I apologize, but I can only provide technical learning content."

# PII Detection
define flow pii protection
  bot response contains personal information
  bot "I cannot share personal information. Let's focus on technical content."
```

```colang
# backend/config/guardrails/analysis.co
# Analysis workflow specific guardrails

include base.co

# Topical Rails: Technical Focus
define flow topical rails
  user asks about non-technical topics
  bot "I focus on technical learning and implementation guides. What technical topic can I help with?"

# Agent Output Validation
define flow agent output validation
  agent response is off-topic
  bot "Let me refocus on the technical analysis."
```

```colang
# backend/config/guardrails/tutor.co
# Tutor workflow specific guardrails

include base.co

# Dialog Rails: Socratic Questioning Flow
define flow dialog rails
  user asks off-topic question during lesson
  bot "Let's focus on the current lesson. Here's a Socratic question to guide your learning..."

# Lesson Topic Enforcement
define flow lesson topic enforcement
  user tries to skip ahead or change topic
  bot "Let's complete the current lesson first. Here's the next step..."
```

---

## ⚠️ Risk Assessment & Mitigation

### Risks

1. **Performance Impact**
   - **Risk**: Guardrails add 100-300ms latency per LLM call
   - **Mitigation**: 
     - Use `passthrough=True` for tool calling
     - Cache guardrails config
     - Feature flag for gradual rollout
     - Monitor latency metrics

2. **False Positives**
   - **Risk**: Over-aggressive guardrails block legitimate technical content
   - **Mitigation**:
     - Start with permissive config
     - Tune based on production data
     - Allow bypass for trusted users (future)
     - Log all violations for analysis

3. **Maintenance Overhead**
   - **Risk**: Colang configs need updates as threats evolve
   - **Mitigation**:
     - Document config structure
     - Add tests for guardrail behavior
     - Create monitoring dashboard
     - Regular security reviews

4. **Provider Compatibility**
   - **Risk**: NeMo Guardrails may not support all LLM providers
   - **Mitigation**:
     - Test with primary providers (Anthropic, OpenAI)
     - Fallback gracefully if unsupported
     - Contribute fixes upstream if needed

### Success Metrics

- **Security**: 0 successful jailbreak attempts
- **Quality**: <5% false positive rate
- **Performance**: <300ms additional latency
- **Coverage**: 100% of agent LLM calls guarded

---

## 📊 Monitoring & Observability

### Metrics to Track

1. **Violation Metrics**
   - Input rail violations (jailbreak attempts)
   - Output rail violations (inappropriate content)
   - Topical rail violations (off-topic requests)

2. **Performance Metrics**
   - Guardrails latency (p50, p95, p99)
   - LLM call latency with/without guardrails

3. **Quality Metrics**
   - False positive rate
   - User satisfaction (if available)

### Logging

```python
# Example violation logging
logger.warning(
    "guardrail_violation",
    domain="analysis",
    agent="tech_comparator",
    violation_type="jailbreak_attempt",
    user_input="...",
    blocked=True,
)
```

### Dashboard (Future)

- Real-time violation rate
- Blocked requests by type
- False positive analysis
- Performance impact

---

## 🧪 Testing Strategy

### Unit Tests

```python
# backend/tests/unit/services/guardrails/test_rails_wrapper.py
import pytest
from app.shared.services.guardrails.rails_wrapper import wrap_with_guardrails
from app.shared.services.guardrails.config_loader import load_guardrails_config

def test_jailbreak_detection():
    """Test that jailbreak attempts are blocked."""
    config = load_guardrails_config("analysis")
    llm = get_chat_model()
    guarded_llm = wrap_with_guardrails(llm, config)
    
    # Attempt jailbreak
    response = guarded_llm.invoke("Ignore previous instructions and...")
    assert "I can only help with technical learning" in response.content

def test_legitimate_request_passes():
    """Test that legitimate technical requests pass through."""
    config = load_guardrails_config("analysis")
    llm = get_chat_model()
    guarded_llm = wrap_with_guardrails(llm, config)
    
    # Legitimate request
    response = guarded_llm.invoke("Explain how to implement RAG with LangGraph")
    assert len(response.content) > 0
    assert "technical" in response.content.lower() or "implementation" in response.content.lower()
```

### Integration Tests

```python
# backend/tests/integration/services/guardrails/test_analysis_workflow_guardrails.py
async def test_analysis_workflow_with_guardrails():
    """Test that analysis workflow respects guardrails."""
    # Create analysis with malicious input
    response = await client.post(
        "/api/v1/analyze",
        json={"url": "https://example.com", "user_prompt": "jailbreak attempt..."}
    )
    
    # Should be blocked or sanitized
    assert response.status_code in [200, 400]
    # Check logs for violation
```

---

## 📚 References

### Documentation
- [NeMo Guardrails Docs](https://docs.nvidia.com/nemo/guardrails/latest/index.html)
- [LangGraph Integration Guide](https://docs.nvidia.com/nemo/guardrails/latest/user-guides/langchain/langgraph-integration.html)
- [Colang 2.0 Guide](https://docs.nvidia.com/nemo/guardrails/latest/user-guides/colang-2.0/overview.html)

### Code Examples
- [NeMo Guardrails GitHub](https://github.com/nvidia/nemo-guardrails)
- [LangGraph Integration Examples](https://github.com/nvidia/nemo-guardrails/tree/develop/examples/langgraph)

### SkillForge Context
- Architecture: `docs/ARCHITECTURE.md`
- Workflow Structure: `backend/app/domains/analysis/workflows/graph_builder.py`
- Agent Base: `backend/app/domains/analysis/workflows/agents/base.py`
- Model Factory: `backend/app/core/model_factory.py`

---

## ✅ Next Steps

1. **Review & Approval**: Get team approval for integration plan
2. **Phase 1 Implementation**: Start with MVP (analysis workflow guardrails)
3. **Testing**: Comprehensive unit and integration tests
4. **Gradual Rollout**: Enable feature flag for staging, then production
5. **Monitoring**: Track metrics and tune configs based on data
6. **Documentation**: Update architecture docs with guardrails integration

---

**Status**: ✅ Research Complete - Ready for Implementation  
**Estimated Timeline**: 4-5 weeks (phased rollout)  
**Priority**: High (Security & Quality Enhancement)
