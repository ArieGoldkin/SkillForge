/**
 * Agent-specific error explanations (non-critical)
 */
import type { ErrorExplanation } from './types'

export const AGENT_ERRORS: Record<string, ErrorExplanation> = {
  TECH_COMPARATOR_FAILED: {
    title: 'Technology Comparison Failed',
    reason: 'Unable to compare technologies from this content',
    action:
      'This stage requires technology comparisons. The analysis will continue without this stage',
    retryable: true,
    severity: 'non-critical',
  },
  SECURITY_AUDITOR_FAILED: {
    title: 'Security Audit Failed',
    reason: 'Unable to perform security analysis on this content',
    action:
      'This stage requires security-related content. The analysis will continue without this stage',
    retryable: true,
    severity: 'non-critical',
  },
  IMPLEMENTATION_PLANNER_FAILED: {
    title: 'Implementation Planning Failed',
    reason: 'Unable to generate implementation plan from this content',
    action:
      'This stage requires implementation details. The analysis will continue without this stage',
    retryable: true,
    severity: 'non-critical',
  },
  PERFORMANCE_ANALYST_FAILED: {
    title: 'Performance Analysis Failed',
    reason: 'Unable to analyze performance aspects from this content',
    action:
      'This stage requires performance metrics. The analysis will continue without this stage',
    retryable: true,
    severity: 'non-critical',
  },
  CODE_QUALITY_CRITIC_FAILED: {
    title: 'Code Quality Review Failed',
    reason: 'Unable to review code quality from this content',
    action: 'This stage requires code examples. The analysis will continue without this stage',
    retryable: true,
    severity: 'non-critical',
  },
  TREND_VALIDATOR_FAILED: {
    title: 'Trend Analysis Failed',
    reason: 'Unable to validate technology trends from this content',
    action: 'This stage requires technology trends. The analysis will continue without this stage',
    retryable: true,
    severity: 'non-critical',
  },
  DEPENDENCY_MAPPER_FAILED: {
    title: 'Dependency Mapping Failed',
    reason: 'Unable to map dependencies from this content',
    action:
      'This stage requires dependency information. The analysis will continue without this stage',
    retryable: true,
    severity: 'non-critical',
  },
  INTEGRATION_FEASIBILITY_FAILED: {
    title: 'Integration Feasibility Check Failed',
    reason: 'Unable to assess integration feasibility from this content',
    action:
      'This stage requires integration details. The analysis will continue without this stage',
    retryable: true,
    severity: 'non-critical',
  },
}
