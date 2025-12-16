"""Agent output schemas for analysis domain.

These schemas define the structured outputs from specialized analysis agents.
"""

# Re-export all agent schemas for convenience
from app.domains.analysis.schemas.agents.base import (
    DataAvailabilityLevel,
    DataAvailabilityMixin,
)
from app.domains.analysis.schemas.agents.code_quality_critic import (
    CodeIssue,
    CodeQualityReview,
)
from app.domains.analysis.schemas.agents.dependency_mapper import (
    Dependency,
    DependencyMapping,
)
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
from app.domains.analysis.schemas.agents.security_auditor import (
    SecurityAudit,
    SecurityRisk,
)
from app.domains.analysis.schemas.agents.tech_comparator import (
    TechComparison,
    TechComparisonEntry,
)
from app.domains.analysis.schemas.agents.trend_validator import (
    TrendAssessment,
    TrendValidation,
)

__all__ = [
    "CodeIssue",
    "CodeQualityReview",
    "CompatibilityScore",
    "DataAvailabilityLevel",
    "DataAvailabilityMixin",
    "Dependency",
    "DependencyMapping",
    "ImplementationPlan",
    "ImplementationStep",
    "IntegrationFeasibility",
    "PerformanceAnalysis",
    "PerformanceMetric",
    "SecurityAudit",
    "SecurityRisk",
    "TechComparison",
    "TechComparisonEntry",
    "TrendAssessment",
    "TrendValidation",
]
