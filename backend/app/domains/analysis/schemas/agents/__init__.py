"""Agent output schemas for analysis domain.

These schemas define the structured outputs from specialized analysis agents.
"""

# Re-export all agent schemas for convenience
from app.domains.analysis.schemas.agents.actionable import (
    Action,
    ActionableOutput,
    Resource,
)
from app.domains.analysis.schemas.agents.alternatives_finder import (
    Alternative,
    AlternativesFinderOutput,
)
from app.domains.analysis.schemas.agents.audience_fit import (
    Audience,
    AudienceFitOutput,
)
from app.domains.analysis.schemas.agents.base import (
    DataAvailabilityLevel,
    DataAvailabilityMixin,
)
from app.domains.analysis.schemas.agents.code_quality_critic import (
    CodeIssue,
    CodeQualityReview,
)
from app.domains.analysis.schemas.agents.community_pulse import (
    CommunityConcern,
    CommunityPulseOutput,
    Discussion,
    GitHubMetrics,
)
from app.domains.analysis.schemas.agents.deep_researcher import (
    DeepResearcherOutput,
    ResearchFinding,
)
from app.domains.analysis.schemas.agents.dependency_mapper import (
    Dependency,
    DependencyMapping,
)
from app.domains.analysis.schemas.agents.fact_validator import (
    Claim,
    FactValidatorOutput,
)
from app.domains.analysis.schemas.agents.implementation_planner import (
    ImplementationPlan,
    ImplementationStep,
)
from app.domains.analysis.schemas.agents.integration_feasibility import (
    CompatibilityScore,
    IntegrationFeasibility,
)
from app.domains.analysis.schemas.agents.key_insights import (
    KeyInsight,
    KeyInsightsOutput,
)
from app.domains.analysis.schemas.agents.knowledge_curator import (
    KnowledgeConnection,
    KnowledgeCuratorOutput,
    RecommendedContent,
)
from app.domains.analysis.schemas.agents.learning_path_advisor import (
    LearningPathAdvisorOutput,
    LearningStep,
    SkillGap,
)
from app.domains.analysis.schemas.agents.performance_analyst import (
    PerformanceAnalysis,
    PerformanceMetric,
)
from app.domains.analysis.schemas.agents.pros_cons import ProsConsOutput
from app.domains.analysis.schemas.agents.security_auditor import (
    SecurityAudit,
    SecurityRisk,
)
from app.domains.analysis.schemas.agents.source_credibility import (
    CredibilitySignal,
    SourceCredibilityOutput,
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
    "Action",
    "ActionableOutput",
    "Alternative",
    "AlternativesFinderOutput",
    "Audience",
    "AudienceFitOutput",
    "Claim",
    "CodeIssue",
    "CodeQualityReview",
    "CommunityConcern",
    "CommunityPulseOutput",
    "CompatibilityScore",
    "CredibilitySignal",
    "DataAvailabilityLevel",
    "DataAvailabilityMixin",
    "DeepResearcherOutput",
    "Dependency",
    "DependencyMapping",
    "Discussion",
    "FactValidatorOutput",
    "GitHubMetrics",
    "ImplementationPlan",
    "ImplementationStep",
    "IntegrationFeasibility",
    "KeyInsight",
    "KeyInsightsOutput",
    "KnowledgeConnection",
    "KnowledgeCuratorOutput",
    "LearningPathAdvisorOutput",
    "LearningStep",
    "PerformanceAnalysis",
    "PerformanceMetric",
    "ProsConsOutput",
    "RecommendedContent",
    "ResearchFinding",
    "Resource",
    "SecurityAudit",
    "SecurityRisk",
    "SkillGap",
    "SourceCredibilityOutput",
    "TechComparison",
    "TechComparisonEntry",
    "TrendAssessment",
    "TrendValidation",
]
