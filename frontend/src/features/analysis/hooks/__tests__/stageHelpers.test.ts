/**
 * Tests for stageHelpers - Stage display and formatting functions
 *
 * These tests validate the helper functions that transform backend
 * stage data into user-friendly UI text.
 */

import { describe, expect, it } from 'vitest'

import {
  getActionDescription,
  getAgentName,
  getStageDescription,
  mapStageStatus,
} from '../stageHelpers'

describe('stageHelpers', () => {
  describe('mapStageStatus', () => {
    it.each([
      ['complete', 'completed'],
      ['running', 'in-progress'],
      ['failed', 'failed'],
      ['pending', 'pending'],
    ] as const)('maps backend status "%s" to UI status "%s"', (backendStatus, expectedUiStatus) => {
      expect(mapStageStatus(backendStatus)).toBe(expectedUiStatus)
    })

    it('returns pending for unknown status', () => {
      // @ts-expect-error - Testing invalid input
      expect(mapStageStatus('unknown')).toBe('pending')
    })
  })

  describe('getAgentName', () => {
    describe('from stage name defaults', () => {
      it.each([
        ['extraction', 'Content Extractor'],
        ['supervisor_routing', 'Supervisor'],
        ['tech_comparison', 'Tech Comparator'],
        ['security_audit', 'Security Auditor'],
        ['implementation_planning', 'Implementation Planner'],
        ['performance_audit', 'Performance Auditor'],
        ['code_quality_audit', 'Code Quality Reviewer'],
        ['trends_analysis', 'Trends Analyst'],
        ['dependencies_analysis', 'Dependencies Analyzer'],
        ['aggregation', 'Aggregator'],
        ['artifact_generation', 'Report Generator'],
      ] as const)('returns "%s" for stage "%s"', (stage, expectedName) => {
        expect(getAgentName(stage)).toBe(expectedName)
      })
    })

    describe('from details.agent', () => {
      it('formats snake_case agent name to Title Case', () => {
        expect(getAgentName('extraction', { agent: 'content_extractor' })).toBe('Content Extractor')
        expect(getAgentName('security_audit', { agent: 'security_analyzer' })).toBe(
          'Security Analyzer'
        )
      })

      it('handles single word agent names', () => {
        expect(getAgentName('aggregation', { agent: 'aggregator' })).toBe('Aggregator')
      })
    })

    it('returns "Agent" for unknown stage without details', () => {
      // @ts-expect-error - Testing invalid input
      expect(getAgentName('unknown_stage')).toBe('Agent')
    })
  })

  describe('getActionDescription', () => {
    describe('running status', () => {
      it.each([
        ['extraction', 'Extracting content from URL...'],
        ['supervisor_routing', 'Routing analysis to specialized agents...'],
        ['tech_comparison', 'Comparing technology patterns...'],
        ['security_audit', 'Auditing security considerations...'],
        ['implementation_planning', 'Planning implementation steps...'],
        ['artifact_generation', 'Generating implementation guide...'],
      ] as const)('returns action text for running %s', (stage, expectedAction) => {
        expect(getActionDescription(stage, 'running')).toBe(expectedAction)
      })
    })

    describe('complete status', () => {
      it('includes word count for extraction stage', () => {
        expect(getActionDescription('extraction', 'complete', { word_count: 1500 })).toBe(
          'Extracted 1500 words from content'
        )
      })

      it('uses findings_summary when available', () => {
        expect(
          getActionDescription('tech_comparison', 'complete', {
            findings_summary: 'Compared React vs Vue, Angular',
          })
        ).toBe('Compared React vs Vue, Angular')
      })

      it('uses insights_count when findings_summary not available', () => {
        expect(
          getActionDescription('security_audit', 'complete', {
            insights_count: 5,
          })
        ).toBe('Found 5 insights')
      })

      it('uses insights_count singular form for 1 insight', () => {
        expect(
          getActionDescription('implementation_planning', 'complete', {
            insights_count: 1,
          })
        ).toBe('Found 1 insight')
      })

      it('returns generic completion for artifact generation', () => {
        expect(
          getActionDescription('artifact_generation', 'complete', {
            artifact_id: 'abc-123',
          })
        ).toBe('Generated implementation guide')
      })

      it('returns completed with stage title for other stages when no rich details', () => {
        expect(getActionDescription('security_audit', 'complete')).toBe('Completed Security Audit')
        expect(getActionDescription('tech_comparison', 'complete')).toBe(
          'Completed Tech Comparison'
        )
      })
    })

    describe('failed status', () => {
      it('shows error message from details', () => {
        expect(
          getActionDescription('tech_comparison', 'failed', {
            error: 'Agent execution failed',
          })
        ).toBe('Failed: Agent execution failed')
      })

      it('truncates long error messages', () => {
        const longError = 'A'.repeat(150)
        const result = getActionDescription('tech_comparison', 'failed', {
          error: longError,
        })
        expect(result).toContain('Failed:')
        expect(result.length).toBeLessThanOrEqual(91) // 80 chars + "Failed: " prefix (8 chars) + "..." (3 chars)
        expect(result).toContain('...')
      })

      it('shows error_code when error message not available', () => {
        expect(
          getActionDescription('security_audit', 'failed', {
            error_code: 'SECURITY_AUDITOR_FAILED',
          })
        ).toBe('Failed: SECURITY_AUDITOR_FAILED')
      })

      it('shows processing time when error details not available', () => {
        expect(
          getActionDescription('tech_comparison', 'failed', {
            processing_time_ms: 3000,
          })
        ).toBe('Failed after 3s')
      })

      it('returns generic failed message when no error details', () => {
        expect(getActionDescription('tech_comparison', 'failed')).toBe('Failed Tech Comparison')
      })
    })

    describe('skipped status', () => {
      it('shows skip reason when available', () => {
        expect(
          getActionDescription('security_audit', 'skipped', {
            skip_reason: 'Not selected by supervisor',
          })
        ).toBe('Skipped: Not selected by supervisor')
      })

      it('returns generic skipped message when no skip reason', () => {
        expect(getActionDescription('tech_comparison', 'skipped')).toBe('Skipped Tech Comparison')
      })
    })

    describe('other statuses', () => {
      it('returns started message for pending status', () => {
        expect(getActionDescription('extraction', 'pending')).toBe('Started Content Extraction')
      })
    })
  })

  describe('getStageDescription', () => {
    describe('complete status with rich details', () => {
      it('uses findings_summary when available', () => {
        expect(
          getStageDescription('tech_comparison', 'complete', {
            findings_summary: 'Compared React vs Vue, Angular',
          })
        ).toBe('Compared React vs Vue, Angular')
      })

      it('uses insights_count when findings_summary not available', () => {
        expect(
          getStageDescription('security_audit', 'complete', {
            insights_count: 5,
          })
        ).toBe('Found 5 insights')
      })

      it('uses insights_count singular form for 1 insight', () => {
        expect(
          getStageDescription('implementation_planning', 'complete', {
            insights_count: 1,
          })
        ).toBe('Found 1 insight')
      })

      it('returns generic "Completed" when no rich details', () => {
        expect(getStageDescription('tech_comparison', 'complete')).toBe('Completed')
      })

      it('includes word count for extraction stage', () => {
        expect(
          getStageDescription('extraction', 'complete', {
            word_count: 1500,
          })
        ).toBe('Extracted 1500 words')
      })
    })

    describe('running status', () => {
      it('uses agent from details if available', () => {
        expect(
          getStageDescription('tech_comparison', 'running', {
            agent: 'tech_comparator',
          })
        ).toBe('Running tech_comparator...')
      })

      it('returns generic "Processing..." when no agent details', () => {
        expect(getStageDescription('tech_comparison', 'running')).toBe('Processing...')
      })
    })

    describe('failed status', () => {
      it('shows error message from details', () => {
        expect(
          getStageDescription('tech_comparison', 'failed', {
            error: 'Agent execution failed',
          })
        ).toBe('Failed: Agent execution failed')
      })

      it('truncates long error messages', () => {
        const longError = 'A'.repeat(150)
        const result = getStageDescription('tech_comparison', 'failed', {
          error: longError,
        })
        expect(result).toContain('Failed:')
        expect(result.length).toBeLessThanOrEqual(111) // 100 chars + "Failed: " prefix (8 chars) + "..." (3 chars)
        expect(result).toContain('...')
      })

      it('shows error_code when error message not available', () => {
        expect(
          getStageDescription('security_audit', 'failed', {
            error_code: 'SECURITY_AUDITOR_FAILED',
          })
        ).toBe('Failed: SECURITY_AUDITOR_FAILED')
      })

      it('shows processing time when error details not available', () => {
        expect(
          getStageDescription('tech_comparison', 'failed', {
            processing_time_ms: 5000,
          })
        ).toBe('Failed after 5s')
      })

      it('returns generic "Failed" when no error details', () => {
        expect(getStageDescription('tech_comparison', 'failed')).toBe('Failed')
      })
    })

    describe('skipped status', () => {
      it('shows skip reason when available', () => {
        expect(
          getStageDescription('security_audit', 'skipped', {
            skip_reason: 'Not applicable for this content type',
          })
        ).toBe('Skipped: Not applicable for this content type')
      })

      it('shows generic message when skipped_by is supervisor_routing', () => {
        expect(
          getStageDescription('code_quality_audit', 'skipped', {
            skipped_by: 'supervisor_routing',
          })
        ).toBe('Skipped by supervisor (not selected for this analysis)')
      })

      it('returns generic "Skipped by supervisor" when no details', () => {
        expect(getStageDescription('tech_comparison', 'skipped')).toBe('Skipped by supervisor')
      })
    })
  })
})
