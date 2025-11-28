/**
 * Tests for stageHelpers - Stage display and formatting functions
 *
 * These tests validate the helper functions that transform backend
 * stage data into user-friendly UI text.
 */

import { describe, expect, it } from 'vitest'

import { getActionDescription, getAgentName, mapStageStatus } from '../stageHelpers'

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

      it('returns generic completion for artifact generation', () => {
        expect(
          getActionDescription('artifact_generation', 'complete', {
            artifact_id: 'abc-123',
          })
        ).toBe('Generated implementation guide')
      })

      it('returns completed with stage title for other stages', () => {
        expect(getActionDescription('security_audit', 'complete')).toBe('Completed Security Audit')
        expect(getActionDescription('tech_comparison', 'complete')).toBe(
          'Completed Tech Comparison'
        )
      })
    })

    describe('other statuses', () => {
      it('returns started message for pending/other statuses', () => {
        expect(getActionDescription('extraction', 'pending')).toBe('Started Content Extraction')
        expect(getActionDescription('security_audit', 'failed')).toBe('Started Security Audit')
      })
    })
  })
})
