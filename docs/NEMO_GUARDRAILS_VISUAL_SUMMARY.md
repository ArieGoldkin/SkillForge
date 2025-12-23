# 🛡️ NeMo Guardrails Integration - Visual Summary

**Quick Reference Guide** for the comprehensive integration plan.

---

## 🎯 Where Guardrails Fit in SkillForge

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER INPUT (API Layer)                        │
└────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  INPUT RAILS    │  🛡️ NEW: Jailbreak Detection
                    │  (Guard Input)  │     Malicious Content Filter
                    └────────┬────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    WORKFLOW LAYER                                │
│                                                                   │
│  ┌──────────────────────┐      ┌──────────────────────┐        │
│  │  Analysis Workflow   │      │   Tutor Workflow      │        │
│  │  (8 Specialized       │      │   (Socratic Q&A)      │        │
│  │   Agents)             │      │                       │        │
│  └──────────┬───────────┘      └──────────┬───────────┘        │
│             │                              │                     │
│             ▼                              ▼                     │
│  ┌──────────────────────────────────────────────────────┐        │
│  │         AGENT NODES (LLM Calls)                      │        │
│  │  • Tech Comparator    • Security Auditor             │        │
│  │  • Implementation     • Performance Analyst         │        │
│  │  • Code Quality       • Trend Validator             │        │
│  │  • Dependency Mapper  • Integration Feasibility     │        │
│  └──────────────────────┬──────────────────────────────┘        │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                           ▼
                    ┌─────────────────┐
                    │  OUTPUT RAILS   │  🛡️ NEW: Content Filtering
                    │ (Guard Output)  │     PII Detection
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  TOPICAL RAILS  │  🛡️ NEW: Technical Focus
                    │ (Topic Control) │     Stay On-Topic
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   LLM MODELS    │
                    │ Claude/GPT/Gemini│
                    └─────────────────┘
```

---

## 📊 Integration Points Matrix

| Component | Input Rails | Output Rails | Topical Rails | Priority |
|-----------|-----------|--------------|---------------|----------|
| **Analysis Workflow** | ✅ | ✅ | ✅ | **HIGH** |
| - Tech Comparator | ✅ | ✅ | ✅ | High |
| - Security Auditor | ✅ | ✅ | ✅ | High |
| - Implementation Planner | ✅ | ✅ | ✅ | High |
| - Performance Analyst | ✅ | ✅ | ✅ | Medium |
| - Code Quality Critic | ✅ | ✅ | ✅ | Medium |
| - Trend Validator | ✅ | ✅ | ✅ | Low |
| - Dependency Mapper | ✅ | ✅ | ✅ | Low |
| - Integration Feasibility | ✅ | ✅ | ✅ | Low |
| **Tutor Workflow** | ✅ | ✅ | ✅ | **MEDIUM** |
| - Socratic Questions | ✅ | ✅ | ✅ | High |
| - Lesson Delivery | ✅ | ✅ | ✅ | Medium |
| **API Endpoints** | ✅ | ❌ | ❌ | **HIGH** |
| - POST /api/v1/analyze | ✅ | ❌ | ❌ | High |
| - POST /api/v1/tutor/* | ✅ | ❌ | ❌ | Medium |

**Legend:**
- ✅ = Implement in Phase 1-2
- ❌ = Not needed or Phase 3+

---

## 🔄 Implementation Flow

```
Phase 1: MVP (Week 1-2)
┌─────────────────────────────────────────────────────────┐
│ 1. Install NeMo Guardrails                              │
│ 2. Create Guardrails Service Module                      │
│ 3. Create Base + Analysis Config (Colang 2.0)           │
│ 4. Integrate with Analysis Workflow Agents               │
│ 5. Add Feature Flag (ENABLE_GUARDRAILS)                 │
│ 6. Unit Tests                                            │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
Phase 2: Tutor (Week 3)
┌─────────────────────────────────────────────────────────┐
│ 1. Create Tutor Config (Colang 2.0)                     │
│ 2. Integrate with Tutor Workflow                        │
│ 3. Dialog Rails for Socratic Flow                      │
│ 4. Integration Tests                                     │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
Phase 3: Advanced (Week 4-5)
┌─────────────────────────────────────────────────────────┐
│ 1. Enhanced Topical Rails                               │
│ 2. Tool/Action Security                                 │
│ 3. Monitoring Dashboard                                 │
│ 4. Configuration Management                             │
└─────────────────────────────────────────────────────────┘
```

---

## 🎨 Code Integration Pattern

### Before (Current)
```python
# backend/app/core/model_factory.py
def get_chat_model(...):
    model = init_chat_model(...)
    return model  # No guardrails
```

### After (With Guardrails)
```python
# backend/app/core/model_factory.py
def get_chat_model(..., domain="analysis"):
    model = init_chat_model(...)
    
    # 🛡️ NEW: Apply guardrails if enabled
    if settings.ENABLE_GUARDRAILS:
        config = load_guardrails_config(domain=domain)
        if config:
            model = wrap_with_guardrails(model, config)
    
    return model
```

### Agent Usage (No Changes Needed!)
```python
# backend/app/domains/analysis/workflows/agents/base.py
# Agents automatically get guardrails via model_factory
agent = create_structured_agent(
    system_prompt=prompt,
    response_schema=Schema,
    tools=tools,
    task_type="agent",  # Guardrails applied automatically
)
```

---

## 📈 Benefits Visualization

```
┌─────────────────────────────────────────────────────────────┐
│                    BENEFITS ANALYSIS                         │
└─────────────────────────────────────────────────────────────┘

Security 🛡️
├─ Jailbreak Prevention: ████████████████████ 100%
├─ Malicious Input Blocking: ████████████████████ 100%
└─ PII Leakage Prevention: ████████████████████ 100%

Quality ✨
├─ On-Topic Enforcement: ████████████████████ 100%
├─ Inappropriate Content Filter: ████████████████████ 100%
└─ Response Quality Control: ████████████████████ 100%

Cost 💰
├─ Block Malicious Requests: ████████████████████ 100%
└─ Reduce Unnecessary LLM Calls: ████████████████████ 100%

Compliance 📋
├─ Audit Trail: ████████████████████ 100%
└─ Safety Violation Logging: ████████████████████ 100%
```

---

## ⚠️ Risk Mitigation

```
┌─────────────────────────────────────────────────────────────┐
│                    RISK MATRIX                               │
└─────────────────────────────────────────────────────────────┘

Risk                    │ Impact │ Probability │ Mitigation
────────────────────────┼────────┼─────────────┼──────────────────
Performance Impact      │ Medium │ High        │ Feature Flag
                        │        │             │ Caching
                        │        │             │ Monitoring
────────────────────────┼────────┼─────────────┼──────────────────
False Positives         │ High   │ Medium      │ Permissive Config
                        │        │             │ Tuning Based on Data
                        │        │             │ Logging
────────────────────────┼────────┼─────────────┼──────────────────
Maintenance Overhead    │ Low    │ Medium      │ Documentation
                        │        │             │ Tests
                        │        │             │ Dashboard
────────────────────────┼────────┼─────────────┼──────────────────
Provider Compatibility  │ Low    │ Low         │ Test Primary Providers
                        │        │             │ Graceful Fallback
```

---

## 📁 File Structure

```
backend/
├── app/
│   ├── core/
│   │   └── model_factory.py          [MODIFY] Add guardrails wrapping
│   ├── shared/
│   │   └── services/
│   │       └── guardrails/           [NEW]
│   │           ├── __init__.py
│   │           ├── config_loader.py  [NEW] Load Colang configs
│   │           └── rails_wrapper.py  [NEW] RunnableRails wrapper
│   └── domains/
│       ├── analysis/
│       │   └── workflows/
│       │       └── agents/
│       │           └── base.py      [NO CHANGE] Auto-guarded via model_factory
│       └── tutor/
│           └── workflows/           [NO CHANGE] Auto-guarded via model_factory
├── config/
│   └── guardrails/                   [NEW]
│       ├── base.co                   [NEW] Shared safety rules
│       ├── analysis.co               [NEW] Analysis workflow rails
│       └── tutor.co                  [NEW] Tutor workflow rails
└── tests/
    └── unit/
        └── services/
            └── guardrails/           [NEW]
                └── test_rails_wrapper.py
```

---

## 🚀 Quick Start Checklist

```
Phase 1: MVP Implementation
┌─────────────────────────────────────────────────────────┐
│ ☐ Install: poetry add nemoguardrails                    │
│ ☐ Create: backend/app/shared/services/guardrails/       │
│ ☐ Create: backend/config/guardrails/base.co              │
│ ☐ Create: backend/config/guardrails/analysis.co          │
│ ☐ Modify: backend/app/core/model_factory.py              │
│ ☐ Add: ENABLE_GUARDRAILS flag in config.py              │
│ ☐ Test: Unit tests for guardrails wrapper                │
│ ☐ Test: Integration tests for analysis workflow          │
│ ☐ Deploy: Enable flag in staging                        │
│ ☐ Monitor: Track violations and performance             │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Success Metrics

```
┌─────────────────────────────────────────────────────────────┐
│                    SUCCESS CRITERIA                          │
└─────────────────────────────────────────────────────────────┘

✅ Security
   └─ 0 successful jailbreak attempts

✅ Quality
   └─ <5% false positive rate

✅ Performance
   └─ <300ms additional latency

✅ Coverage
   └─ 100% of agent LLM calls guarded
```

---

## 📚 Key Resources

- **Full Plan**: `docs/NEMO_GUARDRAILS_INTEGRATION_PLAN.md`
- **NeMo Docs**: https://docs.nvidia.com/nemo/guardrails/latest/
- **LangGraph Integration**: https://docs.nvidia.com/nemo/guardrails/latest/user-guides/langchain/langgraph-integration.html
- **Colang 2.0 Guide**: https://docs.nvidia.com/nemo/guardrails/latest/user-guides/colang-2.0/overview.html

---

**Status**: ✅ Research Complete - Ready for Implementation  
**Next Step**: Review plan and start Phase 1 (MVP)
