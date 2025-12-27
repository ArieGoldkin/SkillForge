"""Schema alignment tests for agent result processing.

This module verifies that AGENT_COUNTABLE_FIELDS in result_processing.py
matches the actual Pydantic schema definitions for all agents (Tier 0 + Tier 1).

Prevents field name mismatches (Issue #584) by testing:
1. All fields in AGENT_COUNTABLE_FIELDS exist in schemas
2. _count_insights() returns > 0 for valid schema data
3. _extract_findings_summary() returns meaningful text

Run: pytest tests/unit/workflows/agents/test_schema_alignment.py -v
"""

import pytest

# Import Content Analysis agent schemas (Tier 0)
from app.domains.analysis.schemas.agents.code_quality_critic import CodeIssue, CodeQualityReview
from app.domains.analysis.schemas.agents.dependency_mapper import Dependency, DependencyMapping
from app.domains.analysis.schemas.agents.implementation_planner import (
    ImplementationPlan,
    ImplementationStep,
)
from app.domains.analysis.schemas.agents.integration_feasibility import (
    CompatibilityScore,
    IntegrationFeasibility,
)
from app.domains.analysis.schemas.agents.performance_analyst import (
    PerformanceAnalysis,
    PerformanceMetric,
)
from app.domains.analysis.schemas.agents.security_auditor import SecurityAudit, SecurityRisk
from app.domains.analysis.schemas.agents.tech_comparator import TechComparison, TechComparisonEntry
from app.domains.analysis.schemas.agents.trend_validator import TrendAssessment, TrendValidation

# Import Tier 1 Universal agent schemas
from app.domains.analysis.schemas.agents.actionable import Action, ActionableOutput, Resource
from app.domains.analysis.schemas.agents.audience_fit import Audience, AudienceFitOutput
from app.domains.analysis.schemas.agents.key_insights import KeyInsight, KeyInsightsOutput
from app.domains.analysis.schemas.agents.pros_cons import ProsConsOutput

# Import result processing functions
from app.domains.analysis.workflows.agents.result_processing import (
    AGENT_COUNTABLE_FIELDS,
    _count_insights,
    _extract_findings_summary,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixtures: Sample Data for Each Agent Schema
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def tech_comparator_data() -> dict:
    """Valid TechComparison schema data."""
    return TechComparison(
        primary_tech="LangGraph",
        alternatives=["LangChain Agents", "CrewAI"],
        comparison={
            "LangGraph": TechComparisonEntry(
                pros=["Low-level control", "Durable execution"],
                cons=["Steeper learning curve"],
                use_cases=["Long-running agents", "Stateful workflows"],
            ),
            "LangChain Agents": TechComparisonEntry(
                pros=["High-level abstraction", "Easy to use"],
                cons=["Less control"],
                use_cases=["Quick prototypes", "Simple agents"],
            ),
        },
        recommendation="Use LangGraph for complex stateful workflows requiring durability.",
        confidence_score=0.85,
        data_availability="sufficient",
    ).model_dump()


@pytest.fixture
def security_auditor_data() -> dict:
    """Valid SecurityAudit schema data."""
    return SecurityAudit(
        security_risks=[
            SecurityRisk(
                risk_type="authentication",
                severity="high",
                description="Missing JWT token validation in API endpoints.",
                mitigation="Implement JWT verification middleware with proper secret management.",
            ),
            SecurityRisk(
                risk_type="injection",
                severity="critical",
                description="SQL injection vulnerability in user input handling.",
                mitigation="Use parameterized queries and input sanitization.",
            ),
        ],
        best_practices=[
            "Use HTTPS for all API communications",
            "Implement rate limiting on authentication endpoints",
        ],
        compliance_notes=[
            "OWASP Top 10: Address A01:2021 Broken Access Control",
            "GDPR: Ensure user data encryption at rest",
        ],
        recommendation="Prioritize fixing critical SQL injection vulnerability before production deployment.",
        confidence_score=0.90,
        data_availability="sufficient",
    ).model_dump()


@pytest.fixture
def implementation_planner_data() -> dict:
    """Valid ImplementationPlan schema data."""
    return ImplementationPlan(
        prerequisites=["Node.js 18+", "PostgreSQL 14+", "Docker installed"],
        steps=[
            ImplementationStep(
                step=1,
                action="Create database schema with migrations",
                files=["migrations/001_create_users.sql", "models/user.py"],
            ),
            ImplementationStep(
                step=2,
                action="Implement authentication endpoints",
                files=["api/auth.py", "services/auth_service.py"],
            ),
            ImplementationStep(
                step=3,
                action="Add JWT token validation middleware",
                files=["middleware/auth.py"],
            ),
        ],
        testing_strategy="Write unit tests for auth service, integration tests for API endpoints, and manual testing with Postman.",
        estimated_time="4-6 hours",
        confidence_score=0.88,
        data_availability="sufficient",
    ).model_dump()


@pytest.fixture
def performance_analyst_data() -> dict:
    """Valid PerformanceAnalysis schema data."""
    return PerformanceAnalysis(
        performance_metrics=[
            PerformanceMetric(
                metric_name="latency",
                current_value="250ms p95",
                target_value="<100ms p95",
                notes="High latency due to N+1 database queries.",
            ),
            PerformanceMetric(
                metric_name="throughput",
                current_value="500 req/s",
                target_value="2000 req/s",
                notes="Limited by single-threaded processing.",
            ),
        ],
        bottlenecks=[
            "N+1 queries in user profile endpoint causing 200ms+ latency",
            "Synchronous processing blocking request handling",
        ],
        optimization_opportunities=[
            "Add database query batching with DataLoader pattern",
            "Implement Redis caching for frequently accessed user profiles",
            "Use async workers for background tasks",
        ],
        scaling_considerations="Implement horizontal scaling with Redis for session storage and use database read replicas for query optimization.",
        recommendation="Priority 1: Fix N+1 queries with DataLoader. Priority 2: Add Redis caching layer.",
        confidence_score=0.87,
        data_availability="sufficient",
    ).model_dump()


@pytest.fixture
def code_quality_critic_data() -> dict:
    """Valid CodeQualityReview schema data."""
    return CodeQualityReview(
        code_issues=[
            CodeIssue(
                issue_type="antipattern",
                severity="high",
                description="God object pattern in UserService class with 20+ methods.",
                suggestion="Refactor UserService into smaller single-responsibility services.",
            ),
            CodeIssue(
                issue_type="code_smell",
                severity="medium",
                description="Duplicate validation logic across 5 API endpoints.",
                suggestion="Extract validation logic into reusable middleware functions.",
            ),
        ],
        best_practices=[
            "Follow SOLID principles, especially Single Responsibility",
            "Apply DRY principle to eliminate duplicate code",
        ],
        maintainability_score=0.65,
        refactoring_suggestions=[
            "Extract method for complex authentication logic",
            "Rename variables to follow project naming conventions",
            "Replace magic numbers with named constants",
        ],
        recommendation="Refactor God object as priority 1 to improve testability and maintainability.",
        confidence_score=0.82,
        data_availability="sufficient",
    ).model_dump()


@pytest.fixture
def trend_validator_data() -> dict:
    """Valid TrendValidation schema data."""
    return TrendValidation(
        trend_assessments=[
            TrendAssessment(
                category="framework",
                trend_status="current",
                evidence="LangGraph has 15k+ GitHub stars and active development in 2025.",
                adoption_rate="growing",
            ),
            TrendAssessment(
                category="pattern",
                trend_status="emerging",
                evidence="Multi-agent workflows seeing 300% growth in enterprise adoption.",
                adoption_rate="growing",
            ),
        ],
        modern_alternatives=["CrewAI", "AutoGen"],
        future_outlook="LangGraph expected to become de facto standard for stateful agent workflows by 2026. Community ecosystem growing rapidly.",
        recommendation="Adopt LangGraph now for production workflows. Strong community support and active development ensure long-term viability.",
        confidence_score=0.78,
        data_availability="sufficient",
    ).model_dump()


@pytest.fixture
def dependency_mapper_data() -> dict:
    """Valid DependencyMapping schema data."""
    return DependencyMapping(
        required_dependencies=[
            Dependency(
                name="fastapi",
                version="^0.109.0",
                purpose="Core web framework for building REST APIs.",
                compatibility="compatible",
            ),
            Dependency(
                name="sqlalchemy",
                version="^2.0.0",
                purpose="ORM for database interactions with type safety.",
                compatibility="compatible",
            ),
        ],
        optional_dependencies=[
            Dependency(
                name="redis",
                version="^5.0.0",
                purpose="Caching layer for performance optimization.",
                compatibility="compatible",
            ),
        ],
        primary_framework="fastapi",
        core_dependencies=[
            Dependency(
                name="pydantic",
                version="^2.5.0",
                purpose="Data validation and serialization for FastAPI.",
                compatibility="compatible",
            ),
            Dependency(
                name="starlette",
                version="^0.36.0",
                purpose="ASGI framework underlying FastAPI.",
                compatibility="compatible",
            ),
            Dependency(
                name="uvicorn",
                version="^0.27.0",
                purpose="ASGI server for running FastAPI applications.",
                compatibility="compatible",
            ),
        ],
        optional_dependencies_by_purpose={
            "database": [
                Dependency(
                    name="alembic",
                    version="^1.13.0",
                    purpose="Database migration management.",
                    compatibility="compatible",
                ),
            ],
            "auth": [
                Dependency(
                    name="python-jose",
                    version="^3.3.0",
                    purpose="JWT token generation and validation.",
                    compatibility="compatible",
                ),
            ],
        },
        alternatives={
            "database": ["prisma", "tortoise-orm"],
            "auth": ["authlib", "passlib"],
        },
        version_matrix={
            "fastapi": ">=0.109.0 <1.0.0",
            "pydantic": ">=2.5.0 <3.0.0",
        },
        version_conflicts=[
            "Pydantic v1 incompatible with FastAPI 0.109+ which requires Pydantic v2"
        ],
        peer_dependencies=["Python >=3.11"],
        installation_notes=[
            "Install with: pip install fastapi[all] sqlalchemy",
            "Run migrations with: alembic upgrade head",
        ],
        recommendation="Use FastAPI 0.109+ with Pydantic v2 for best type safety. Add Redis for production caching.",
        confidence_score=0.91,
        data_availability="sufficient",
    ).model_dump()


@pytest.fixture
def integration_feasibility_data() -> dict:
    """Valid IntegrationFeasibility schema data."""
    return IntegrationFeasibility(
        compatibility={
            "react": CompatibilityScore(
                score=0.9,
                notes="Native support for React via REST API integration.",
            ),
            "nextjs": CompatibilityScore(
                score=0.85,
                notes="SSR compatible with server-side data fetching.",
            ),
        },
        migration_effort="medium",
        breaking_changes=[
            "API endpoint structure changed from v1 to v2 format",
            "Authentication now requires JWT instead of session cookies",
        ],
        integration_steps=[
            "Install SDK package via npm install @company/sdk",
            "Configure API credentials in environment variables",
            "Replace existing API client with new SDK wrapper",
            "Update authentication flow to use JWT tokens",
        ],
        confidence_score=0.83,
        data_availability="sufficient",
    ).model_dump()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixtures: Tier 1 Universal Agents
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def actionable_data() -> dict:
    """Valid ActionableOutput schema data."""
    return ActionableOutput(
        immediate_actions=[
            Action(
                step_number=1,
                action="Install LangGraph with pip install langgraph",
                expected_outcome="LangGraph installed and importable in Python",
                time_estimate="5 minutes",
            ),
            Action(
                step_number=2,
                action="Run the hello-world example from the docs",
                expected_outcome="Working state graph that prints 'Hello, World!'",
                time_estimate="15 minutes",
            ),
        ],
        follow_up_actions=[
            Action(
                step_number=1,
                action="Implement state persistence with SQLite checkpoint",
                expected_outcome="Durable workflow that survives restarts",
                time_estimate="2 hours",
            ),
        ],
        resources=[
            Resource(
                name="LangGraph Documentation",
                url="https://langchain-ai.github.io/langgraph/",
                resource_type="documentation",
                relevance="Official docs with API reference and examples",
            ),
            Resource(
                name="LangGraph GitHub",
                url="https://github.com/langchain-ai/langgraph",
                resource_type="library",
                relevance="Source code and issue tracker",
            ),
        ],
        quick_win="Install LangGraph and run hello-world example - takes 15 minutes and validates your environment.",
        confidence_score=0.88,
        data_availability="sufficient",
    ).model_dump()


@pytest.fixture
def key_insights_data() -> dict:
    """Valid KeyInsightsOutput schema data."""
    return KeyInsightsOutput(
        insights=[
            KeyInsight(
                title="State persistence enables durable execution",
                description="LangGraph's checkpoint system allows workflows to survive crashes and restarts. This is critical for long-running agent tasks that may take hours.",
                importance="high",
                novelty_score=0.8,
            ),
            KeyInsight(
                title="Graph-based architecture provides fine-grained control",
                description="Unlike chain-based approaches, graphs allow conditional branching and cycles. This enables more complex agent behaviors.",
                importance="high",
                novelty_score=0.7,
            ),
            KeyInsight(
                title="Human-in-the-loop patterns built-in",
                description="LangGraph supports interrupt and resume patterns for human approval workflows.",
                importance="medium",
                novelty_score=0.6,
            ),
        ],
        summary="LangGraph provides durable, graph-based agent workflows with built-in state persistence and human-in-the-loop support.",
        confidence_score=0.85,
        data_availability="sufficient",
    ).model_dump()


@pytest.fixture
def pros_cons_data() -> dict:
    """Valid ProsConsOutput schema data."""
    return ProsConsOutput(
        pros=[
            "State persistence enables crash recovery",
            "Fine-grained control over agent execution",
            "Built-in support for human-in-the-loop",
            "Strong typing with Pydantic state models",
        ],
        cons=[
            "Steeper learning curve than LangChain agents",
            "More boilerplate code required",
            "Smaller community compared to alternatives",
        ],
        verdict="LangGraph is the best choice for production agent workflows requiring durability and control. The learning curve pays off in reliability.",
        recommendation="recommended",
        confidence_score=0.82,
        data_availability="sufficient",
    ).model_dump()


@pytest.fixture
def audience_fit_data() -> dict:
    """Valid AudienceFitOutput schema data."""
    return AudienceFitOutput(
        primary_audience=Audience(
            name="Backend Engineers building AI agents",
            experience_level="intermediate",
            relevance_score=0.95,
            why_relevant="Content covers production patterns for agent orchestration with practical code examples.",
        ),
        secondary_audiences=[
            Audience(
                name="AI/ML Engineers exploring agent frameworks",
                experience_level="advanced",
                relevance_score=0.8,
                why_relevant="Comparison of LangGraph vs alternatives useful for framework selection.",
            ),
        ],
        prerequisites=[
            "Python async/await understanding",
            "Basic familiarity with LLM APIs",
            "Understanding of state machines helpful",
        ],
        not_suitable_for=[
            "Complete beginners to programming",
            "Frontend-only developers",
        ],
        confidence_score=0.79,
        data_availability="sufficient",
    ).model_dump()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Schema Field Existence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.parametrize(
    ("agent_type", "schema_class"),
    [
        # Content Analysis Agents (Tier 0)
        ("tech_comparator", TechComparison),
        ("security_auditor", SecurityAudit),
        ("implementation_planner", ImplementationPlan),
        ("performance_analyst", PerformanceAnalysis),
        ("code_quality_critic", CodeQualityReview),
        ("trend_validator", TrendValidation),
        ("dependency_mapper", DependencyMapping),
        ("integration_feasibility", IntegrationFeasibility),
        # Tier 1: Universal Agents
        ("actionable", ActionableOutput),
        ("key_insights", KeyInsightsOutput),
        ("pros_cons", ProsConsOutput),
        ("audience_fit", AudienceFitOutput),
    ],
)
def test_agent_countable_fields_exist_in_schema(agent_type: str, schema_class: type) -> None:
    """Verify all fields in AGENT_COUNTABLE_FIELDS exist in actual schemas.

    Args:
        agent_type: Agent type key (e.g., "tech_comparator")
        schema_class: Pydantic schema class to validate against

    """
    # Arrange
    expected_fields = AGENT_COUNTABLE_FIELDS[agent_type]
    schema_fields = schema_class.model_fields.keys()  # type: ignore[attr-defined]

    # Act & Assert
    for field_name in expected_fields:
        assert field_name in schema_fields, (
            f"Field '{field_name}' in AGENT_COUNTABLE_FIELDS['{agent_type}'] "
            f"not found in {schema_class.__name__} schema. "
            f"Available fields: {list(schema_fields)}"
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: _count_insights Returns > 0 for Valid Data
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.parametrize(
    ("agent_type", "fixture_name", "expected_min_count"),
    [
        # Content Analysis Agents (Tier 0)
        ("tech_comparator", "tech_comparator_data", 2),  # 2 alternatives
        (
            "security_auditor",
            "security_auditor_data",
            4,
        ),  # 2 risks + 2 best_practices + 2 compliance_notes = 6
        ("implementation_planner", "implementation_planner_data", 3),  # 3 steps
        ("performance_analyst", "performance_analyst_data", 5),  # 2 bottlenecks + 3 optimizations
        ("code_quality_critic", "code_quality_critic_data", 4),  # 2 issues + 2 best_practices
        ("trend_validator", "trend_validator_data", 2),  # 2 trend_assessments
        ("dependency_mapper", "dependency_mapper_data", 6),  # 2 required + 1 optional + 3 core = 6
        (
            "integration_feasibility",
            "integration_feasibility_data",
            6,
        ),  # 2 breaking_changes + 4 integration_steps
        # Tier 1: Universal Agents
        ("actionable", "actionable_data", 5),  # 2 immediate + 1 follow_up + 2 resources = 5
        ("key_insights", "key_insights_data", 3),  # 3 insights
        ("pros_cons", "pros_cons_data", 7),  # 4 pros + 3 cons = 7
        ("audience_fit", "audience_fit_data", 6),  # 1 secondary + 3 prereqs + 2 not_suitable = 6
    ],
)
def test_count_insights_returns_positive_for_valid_data(
    agent_type: str,
    fixture_name: str,
    expected_min_count: int,
    request: pytest.FixtureRequest,
) -> None:
    """Verify _count_insights returns > 0 for valid schema data.

    Args:
        agent_type: Agent type key
        fixture_name: Name of fixture containing valid data
        expected_min_count: Minimum expected insight count
        request: Pytest fixture request for dynamic fixture access

    """
    # Arrange
    findings = request.getfixturevalue(fixture_name)

    # Act
    count = _count_insights(findings, agent_type)

    # Assert
    assert count > 0, f"Expected insights > 0, got {count} for {agent_type}"
    assert count >= expected_min_count, (
        f"Expected at least {expected_min_count} insights for {agent_type}, got {count}"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: _extract_findings_summary Returns Meaningful Text
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.parametrize(
    ("agent_type", "fixture_name", "expected_keywords"),
    [
        # Content Analysis Agents (Tier 0)
        ("tech_comparator", "tech_comparator_data", ["Compared", "LangGraph"]),
        ("security_auditor", "security_auditor_data", ["Found", "security risks"]),
        ("implementation_planner", "implementation_planner_data", ["Planned", "steps"]),
        (
            "performance_analyst",
            "performance_analyst_data",
            ["Identified", "bottlenecks", "optimizations"],
        ),
        ("code_quality_critic", "code_quality_critic_data", ["Found", "issues", "best practices"]),
        ("trend_validator", "trend_validator_data", ["Validated", "trends"]),
        ("dependency_mapper", "dependency_mapper_data", ["Mapped", "dependencies"]),
        (
            "integration_feasibility",
            "integration_feasibility_data",
            ["Identified", "integration steps", "breaking changes"],
        ),
        # Tier 1: Universal Agents
        (
            "actionable",
            "actionable_data",
            ["Extracted", "immediate actions", "follow-ups", "resources"],
        ),
        ("key_insights", "key_insights_data", ["Identified", "key insights"]),
        ("pros_cons", "pros_cons_data", ["Found", "pros", "cons"]),
        ("audience_fit", "audience_fit_data", ["Identified", "audiences", "prerequisites"]),
    ],
)
def test_extract_findings_summary_returns_meaningful_text(
    agent_type: str,
    fixture_name: str,
    expected_keywords: list[str],
    request: pytest.FixtureRequest,
) -> None:
    """Verify _extract_findings_summary returns meaningful text (not generic fallback).

    Args:
        agent_type: Agent type key
        fixture_name: Name of fixture containing valid data
        expected_keywords: Keywords that should appear in summary
        request: Pytest fixture request for dynamic fixture access

    """
    # Arrange
    findings = request.getfixturevalue(fixture_name)

    # Act
    summary = _extract_findings_summary(findings, agent_type)

    # Assert - should NOT be generic fallback
    assert summary != "Analysis complete", (
        f"Expected meaningful summary for {agent_type}, got generic fallback: '{summary}'"
    )

    # Assert - should contain expected keywords
    for keyword in expected_keywords:
        assert keyword.lower() in summary.lower(), (
            f"Expected keyword '{keyword}' in summary for {agent_type}, got: '{summary}'"
        )

    # Assert - should not be empty
    assert len(summary) > 10, f"Expected non-trivial summary for {agent_type}, got: '{summary}'"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Edge Cases - Empty Lists
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.parametrize(
    ("agent_type", "empty_findings"),
    [
        # Content Analysis Agents (Tier 0)
        (
            "tech_comparator",
            {
                "primary_tech": "LangGraph",
                "alternatives": [],
                "comparison": {},
                "recommendation": "Test",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        (
            "security_auditor",
            {
                "security_risks": [],
                "best_practices": [],
                "compliance_notes": [],
                "recommendation": "Test",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        (
            "implementation_planner",
            {
                "prerequisites": [],
                "steps": [],
                "testing_strategy": "Test",
                "estimated_time": "1 hour",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        (
            "performance_analyst",
            {
                "performance_metrics": [],
                "bottlenecks": [],
                "optimization_opportunities": [],
                "scaling_considerations": "Test",
                "recommendation": "Test",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        (
            "code_quality_critic",
            {
                "code_issues": [],
                "best_practices": [],
                "maintainability_score": 0.5,
                "refactoring_suggestions": [],
                "recommendation": "Test",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        (
            "trend_validator",
            {
                "trend_assessments": [],
                "modern_alternatives": [],
                "future_outlook": "Test",
                "recommendation": "Test",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        (
            "dependency_mapper",
            {
                "required_dependencies": [],
                "optional_dependencies": [],
                "core_dependencies": [],
                "recommendation": "Test",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        (
            "integration_feasibility",
            {
                "compatibility": {},
                "migration_effort": "medium",
                "breaking_changes": [],
                "integration_steps": [],
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        # Tier 1: Universal Agents
        (
            "actionable",
            {
                "immediate_actions": [],
                "follow_up_actions": [],
                "resources": [],
                "quick_win": "Test",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        (
            "key_insights",
            {
                "insights": [],
                "summary": "Test",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        (
            "pros_cons",
            {
                "pros": [],
                "cons": [],
                "verdict": "Test",
                "recommendation": "neutral",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        (
            "audience_fit",
            {
                "primary_audience": {
                    "name": "Test",
                    "experience_level": "beginner",
                    "relevance_score": 0.5,
                    "why_relevant": "Test",
                },
                "secondary_audiences": [],
                "prerequisites": [],
                "not_suitable_for": [],
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
    ],
)
def test_count_insights_handles_empty_lists_gracefully(
    agent_type: str,
    empty_findings: dict,
) -> None:
    """Verify _count_insights handles empty list fields gracefully.

    Args:
        agent_type: Agent type key
        empty_findings: Findings dict with empty lists

    """
    # Act
    count = _count_insights(empty_findings, agent_type)

    # Assert - should return 0 for truly empty findings
    assert count == 0, f"Expected 0 insights for empty {agent_type} findings, got {count}"


@pytest.mark.parametrize(
    ("agent_type", "empty_findings"),
    [
        # Content Analysis Agents (Tier 0)
        (
            "tech_comparator",
            {
                "primary_tech": "LangGraph",
                "alternatives": [],
                "comparison": {},
                "recommendation": "Test",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        (
            "performance_analyst",
            {
                "performance_metrics": [],
                "bottlenecks": [],
                "optimization_opportunities": [],
                "scaling_considerations": "Test",
                "recommendation": "Test",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        (
            "code_quality_critic",
            {
                "code_issues": [],
                "best_practices": [],
                "maintainability_score": 0.5,
                "refactoring_suggestions": [],
                "recommendation": "Test",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        (
            "trend_validator",
            {
                "trend_assessments": [],
                "modern_alternatives": [],
                "future_outlook": "Test",
                "recommendation": "Test",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        (
            "dependency_mapper",
            {
                "required_dependencies": [],
                "optional_dependencies": [],
                "core_dependencies": [],
                "recommendation": "Test",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        # Tier 1: Universal Agents
        (
            "actionable",
            {
                "immediate_actions": [],
                "follow_up_actions": [],
                "resources": [],
                "quick_win": "Test",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        (
            "key_insights",
            {
                "insights": [],
                "summary": "Test",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        (
            "pros_cons",
            {
                "pros": [],
                "cons": [],
                "verdict": "Test",
                "recommendation": "neutral",
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
        (
            "audience_fit",
            {
                "primary_audience": {
                    "name": "Test",
                    "experience_level": "beginner",
                    "relevance_score": 0.5,
                    "why_relevant": "Test",
                },
                "secondary_audiences": [],
                "prerequisites": [],
                "not_suitable_for": [],
                "confidence_score": 0.5,
                "data_availability": "insufficient",
            },
        ),
    ],
)
def test_extract_findings_summary_handles_empty_lists_gracefully(
    agent_type: str,
    empty_findings: dict,
) -> None:
    """Verify _extract_findings_summary handles empty list fields gracefully.

    Args:
        agent_type: Agent type key
        empty_findings: Findings dict with empty lists

    """
    # Act
    summary = _extract_findings_summary(empty_findings, agent_type)

    # Assert - should return fallback text without errors
    assert isinstance(summary, str), f"Expected string summary for empty {agent_type} findings"
    assert len(summary) > 0, f"Expected non-empty summary for empty {agent_type} findings"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: AGENT_COUNTABLE_FIELDS Completeness
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_agent_countable_fields_has_all_agent_types() -> None:
    """Verify AGENT_COUNTABLE_FIELDS includes all 12 agent types (Tier 0 + Tier 1)."""
    # Arrange
    expected_agent_types = {
        # Content Analysis Agents (Tier 0)
        "tech_comparator",
        "security_auditor",
        "implementation_planner",
        "performance_analyst",
        "code_quality_critic",
        "trend_validator",
        "dependency_mapper",
        "integration_feasibility",
        # Tier 1: Universal Agents
        "actionable",
        "key_insights",
        "pros_cons",
        "audience_fit",
    }

    # Act
    actual_agent_types = set(AGENT_COUNTABLE_FIELDS.keys())

    # Assert
    assert actual_agent_types == expected_agent_types, (
        f"AGENT_COUNTABLE_FIELDS missing agent types: {expected_agent_types - actual_agent_types}. "
        f"Extra agent types: {actual_agent_types - expected_agent_types}"
    )


def test_agent_countable_fields_has_no_empty_lists() -> None:
    """Verify AGENT_COUNTABLE_FIELDS has at least 1 field per agent."""
    # Act & Assert
    for agent_type, fields in AGENT_COUNTABLE_FIELDS.items():
        assert len(fields) > 0, f"AGENT_COUNTABLE_FIELDS['{agent_type}'] has empty field list"
