"""Configuration constants for supervisor agent."""

# Supervisor system prompt (compressed for efficiency - 60% reduction)
SUPERVISOR_PROMPT = """Analyze content and select relevant agents. Output JSON:
{"agents": ["agent1", "agent2"], "reasoning": "brief", "confidence": 0.0-1.0}

Agents:
- tech_comparator: Compare tech with modern alternatives
- security_auditor: Security risks/vulnerabilities
- integration_feasibility: Modern stack integration (Next.js, FastAPI)
- implementation_planner: Step-by-step guides/roadmaps
- performance_analyst: Performance trade-offs, latency, scaling
- code_quality_critic: Code patterns, best practices, maintainability
- trend_validator: 2025 trends vs legacy/outdated
- dependency_mapper: Dependencies, versions, conflicts

Select based on: content type, keywords, complexity, analysis needs.

Examples:
- React tutorial → {"agents": ["implementation_planner", "code_quality_critic"],
  "reasoning": "Tutorial needs implementation guide and code review",
  "confidence": 0.9}
- Security guide → {"agents": ["security_auditor", "trend_validator"],
  "reasoning": "Security content needs audit and trend validation",
  "confidence": 0.95}
- API comparison → {"agents": ["tech_comparator", "performance_analyst"],
  "reasoning": "Comparison needs tech analysis and performance evaluation",
  "confidence": 0.85}"""
