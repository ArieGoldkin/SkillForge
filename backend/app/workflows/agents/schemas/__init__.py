"""Pydantic schemas for agent structured outputs.

This module defines the output schemas for all specialized analysis agents.
These schemas are used with ToolStrategy to ensure type-safe, validated
structured output from agents.
"""

# Tech comparator schemas
# Code quality critic schemas
from app.workflows.agents.schemas.code_quality_critic import CodeIssue, CodeQualityReview

# Dependency mapper schemas
from app.workflows.agents.schemas.dependency_mapper import Dependency, DependencyMapping

# Implementation planner schemas
from app.workflows.agents.schemas.implementation_planner import (
    ImplementationPlan,
    ImplementationStep,
)

# Integration feasibility schemas
from app.workflows.agents.schemas.integration_feasibility import (
    CompatibilityScore,
    IntegrationFeasibility,
)

# Performance analyst schemas
from app.workflows.agents.schemas.performance_analyst import PerformanceAnalysis, PerformanceMetric

# Security auditor schemas
from app.workflows.agents.schemas.security_auditor import SecurityAudit, SecurityRisk
from app.workflows.agents.schemas.tech_comparator import TechComparison, TechComparisonEntry

# Trend validator schemas
from app.workflows.agents.schemas.trend_validator import TrendAssessment, TrendValidation

__all__ = [
    "CodeIssue",
    "CodeQualityReview",
    "CompatibilityScore",
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
