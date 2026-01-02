import { describe, expect, it } from 'vitest'

import {
  formatErrorCode,
  getErrorExplanation,
  getErrorCodeBadgeVariant,
  isErrorRetryable,
  isErrorCritical,
} from '../errorCodeFormatter'

describe('errorCodeFormatter', () => {
  describe('formatErrorCode', () => {
    it('formats known error codes correctly', () => {
      expect(formatErrorCode('EXTRACTION_FAILED')).toBe('Content Extraction Failed')
      expect(formatErrorCode('TECH_COMPARATOR_FAILED')).toBe('Technology Comparison Failed')
      expect(formatErrorCode('ANALYSIS_FAILED')).toBe('Analysis Failed')
    })

    it('returns "Unknown Error" for null/undefined', () => {
      expect(formatErrorCode(null)).toBe('Unknown Error')
      expect(formatErrorCode(undefined)).toBe('Unknown Error')
    })

    it('converts unknown error codes to Title Case', () => {
      expect(formatErrorCode('CUSTOM_ERROR_CODE')).toBe('Custom Error Code')
      expect(formatErrorCode('MY_UNKNOWN_ERROR')).toBe('My Unknown Error')
    })
  })

  describe('getErrorExplanation', () => {
    it('returns full explanation for known error codes', () => {
      const explanation = getErrorExplanation('EXTRACTION_FAILED')

      expect(explanation.title).toBe('Content Extraction Failed')
      expect(explanation.reason).toContain('Unable to extract content')
      expect(explanation.action).toContain('Try a different URL')
      expect(explanation.retryable).toBe(true)
      expect(explanation.severity).toBe('critical')
    })

    it('returns fallback explanation for unknown error codes', () => {
      const explanation = getErrorExplanation('UNKNOWN_CODE')

      expect(explanation.title).toBe('Unknown Code')
      expect(explanation.reason).toBe('An error occurred during this stage')
      expect(explanation.action).toBe('Try retrying the analysis')
      expect(explanation.retryable).toBe(true)
      expect(explanation.severity).toBe('non-critical')
    })

    it('returns default explanation for null/undefined', () => {
      const explanation = getErrorExplanation(null)

      expect(explanation.title).toBe('Unknown Error')
      expect(explanation.reason).toBe('An unexpected error occurred')
      expect(explanation.action).toContain('Try retrying')
      expect(explanation.retryable).toBe(true)
      expect(explanation.severity).toBe('critical')
    })

    it('covers all agent error codes', () => {
      const agentCodes = [
        'TECH_COMPARATOR_FAILED',
        'SECURITY_AUDITOR_FAILED',
        'IMPLEMENTATION_PLANNER_FAILED',
        'PERFORMANCE_ANALYST_FAILED',
        'CODE_QUALITY_CRITIC_FAILED',
        'TREND_VALIDATOR_FAILED',
        'DEPENDENCY_MAPPER_FAILED',
        'INTEGRATION_FEASIBILITY_FAILED',
      ]

      agentCodes.forEach((code) => {
        const explanation = getErrorExplanation(code)
        expect(explanation.title).toBeTruthy()
        expect(explanation.reason).toBeTruthy()
        expect(explanation.action).toBeTruthy()
        expect(typeof explanation.retryable).toBe('boolean')
        expect(['critical', 'non-critical']).toContain(explanation.severity)
      })
    })

    it('marks agent errors as non-critical', () => {
      const agentCodes = [
        'TECH_COMPARATOR_FAILED',
        'SECURITY_AUDITOR_FAILED',
        'PERFORMANCE_ANALYST_FAILED',
      ]

      agentCodes.forEach((code) => {
        const explanation = getErrorExplanation(code)
        expect(explanation.severity).toBe('non-critical')
        expect(explanation.action).toContain('continue without this stage')
      })
    })

    it('marks extraction/analysis errors as critical', () => {
      const criticalCodes = [
        'EXTRACTION_FAILED',
        'ANALYSIS_FAILED',
        'QUALITY_GATE_FAILED',
        'ARTIFACT_FAILED',
      ]

      criticalCodes.forEach((code) => {
        const explanation = getErrorExplanation(code)
        expect(explanation.severity).toBe('critical')
      })
    })
  })

  describe('isErrorRetryable', () => {
    it('returns true for retryable errors', () => {
      expect(isErrorRetryable('EXTRACTION_FAILED')).toBe(true)
      expect(isErrorRetryable('TECH_COMPARATOR_FAILED')).toBe(true)
      expect(isErrorRetryable('ANALYSIS_FAILED')).toBe(true)
    })

    it('returns false for non-retryable errors', () => {
      expect(isErrorRetryable('ERROR_PAGE')).toBe(false)
      expect(isErrorRetryable('REDIRECT_LOOP')).toBe(false)
    })

    it('returns true for null/undefined (default retryable)', () => {
      expect(isErrorRetryable(null)).toBe(true)
      expect(isErrorRetryable(undefined)).toBe(true)
    })
  })

  describe('isErrorCritical', () => {
    it('returns true for critical errors', () => {
      expect(isErrorCritical('EXTRACTION_FAILED')).toBe(true)
      expect(isErrorCritical('ANALYSIS_FAILED')).toBe(true)
      expect(isErrorCritical('QUALITY_GATE_FAILED')).toBe(true)
      expect(isErrorCritical('ARTIFACT_FAILED')).toBe(true)
    })

    it('returns false for non-critical errors', () => {
      expect(isErrorCritical('TECH_COMPARATOR_FAILED')).toBe(false)
      expect(isErrorCritical('SECURITY_AUDITOR_FAILED')).toBe(false)
      expect(isErrorCritical('PERFORMANCE_ANALYST_FAILED')).toBe(false)
    })

    it('returns true for null/undefined (default critical)', () => {
      expect(isErrorCritical(null)).toBe(true)
      expect(isErrorCritical(undefined)).toBe(true)
    })
  })

  describe('getErrorCodeBadgeVariant', () => {
    it('returns destructive for critical errors', () => {
      expect(getErrorCodeBadgeVariant('EXTRACTION_FAILED')).toBe('destructive')
      expect(getErrorCodeBadgeVariant('ANALYSIS_FAILED')).toBe('destructive')
    })

    it('returns default for non-critical errors', () => {
      expect(getErrorCodeBadgeVariant('TECH_COMPARATOR_FAILED')).toBe('default')
      expect(getErrorCodeBadgeVariant('SECURITY_AUDITOR_FAILED')).toBe('default')
    })

    it('returns secondary for null/undefined', () => {
      expect(getErrorCodeBadgeVariant(null)).toBe('secondary')
      expect(getErrorCodeBadgeVariant(undefined)).toBe('secondary')
    })
  })

  describe('comprehensive error code coverage', () => {
    const allErrorCodes = [
      // Extraction errors
      'HTTP_404',
      'HTTP_5XX',
      'TIMEOUT',
      'ERROR_PAGE',
      'REDIRECT_LOOP',
      'NETWORK_ERROR',
      'EXTRACTION_FAILED',
      'EXTRACTION_ERROR',
      // Embedding errors
      'EMBEDDING_FAILED',
      'EMBEDDING_ERROR',
      // Analysis errors
      'ANALYSIS_FAILED',
      'QUALITY_GATE_FAILED',
      'QUALITY_VALIDATION_FAILED',
      // Agent errors
      'TECH_COMPARATOR_FAILED',
      'SECURITY_AUDITOR_FAILED',
      'IMPLEMENTATION_PLANNER_FAILED',
      'PERFORMANCE_ANALYST_FAILED',
      'CODE_QUALITY_CRITIC_FAILED',
      'TREND_VALIDATOR_FAILED',
      'DEPENDENCY_MAPPER_FAILED',
      'INTEGRATION_FEASIBILITY_FAILED',
      // Aggregation errors
      'AGGREGATION_FAILED',
      // Artifact errors
      'ARTIFACT_FAILED',
      'ARTIFACT_GENERATION_FAILED',
      // Generic
      'UNKNOWN',
      'WORKFLOW_FAILED',
      'WORKFLOW_STARTUP_FAILED',
      'WORKFLOW_EXECUTION_FAILED',
    ]

    it('has explanations for all error codes', () => {
      allErrorCodes.forEach((code) => {
        const explanation = getErrorExplanation(code)
        expect(explanation.title).toBeTruthy()
        expect(explanation.reason).toBeTruthy()
        expect(explanation.action).toBeTruthy()
      })
    })

    it('has consistent retryability for all error codes', () => {
      allErrorCodes.forEach((code) => {
        const explanation = getErrorExplanation(code)
        const retryable = isErrorRetryable(code)
        expect(retryable).toBe(explanation.retryable)
      })
    })

    it('has consistent severity for all error codes', () => {
      allErrorCodes.forEach((code) => {
        const explanation = getErrorExplanation(code)
        const critical = isErrorCritical(code)
        expect(critical).toBe(explanation.severity === 'critical')
      })
    })
  })
})
