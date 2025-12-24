/**
 * Tests for useStageGroups hook
 *
 * Verifies group status computation and progress calculation
 */

import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { StageName } from '@/schemas/base'

import type { StageStatusEntry } from '../stageConfig'
import { useStageGroups } from '../useStageGroups'

describe('useStageGroups', () => {
  it('should return 7 groups in correct order', () => {
    const stageStatuses = new Map<StageName, StageStatusEntry>()
    const { result } = renderHook(() => useStageGroups(stageStatuses))

    expect(result.current).toHaveLength(7)
    expect(result.current[0].group.id).toBe('core-workflow')
    expect(result.current[1].group.id).toBe('content-analysis')
    expect(result.current[2].group.id).toBe('tier1-universal')
    expect(result.current[3].group.id).toBe('tier2-validation')
    expect(result.current[4].group.id).toBe('tier3-research')
    expect(result.current[5].group.id).toBe('quality-pipeline')
    expect(result.current[6].group.id).toBe('optional-stages')
  })

  it('should compute group status as pending when all stages are pending', () => {
    const stageStatuses = new Map<StageName, StageStatusEntry>([
      ['extraction', { status: 'pending', timestamp: new Date().toISOString() }],
      ['embedding', { status: 'pending', timestamp: new Date().toISOString() }],
      ['supervisor_routing', { status: 'pending', timestamp: new Date().toISOString() }],
    ])

    const { result } = renderHook(() => useStageGroups(stageStatuses))
    const coreWorkflowGroup = result.current[0]

    expect(coreWorkflowGroup.status.status).toBe('pending')
    expect(coreWorkflowGroup.status.progress).toBe(0)
  })

  it('should compute group status as in-progress when any stage is running', () => {
    const stageStatuses = new Map<StageName, StageStatusEntry>([
      ['extraction', { status: 'complete', timestamp: new Date().toISOString() }],
      ['embedding', { status: 'running', timestamp: new Date().toISOString() }],
      ['supervisor_routing', { status: 'pending', timestamp: new Date().toISOString() }],
    ])

    const { result } = renderHook(() => useStageGroups(stageStatuses))
    const coreWorkflowGroup = result.current[0]

    expect(coreWorkflowGroup.status.status).toBe('in-progress')
    expect(coreWorkflowGroup.status.running).toBe(1)
  })

  it('should compute group status as completed when all stages are complete', () => {
    const stageStatuses = new Map<StageName, StageStatusEntry>([
      ['extraction', { status: 'complete', timestamp: new Date().toISOString() }],
      ['embedding', { status: 'complete', timestamp: new Date().toISOString() }],
      ['supervisor_routing', { status: 'complete', timestamp: new Date().toISOString() }],
    ])

    const { result } = renderHook(() => useStageGroups(stageStatuses))
    const coreWorkflowGroup = result.current[0]

    expect(coreWorkflowGroup.status.status).toBe('completed')
    expect(coreWorkflowGroup.status.progress).toBe(100)
    expect(coreWorkflowGroup.status.completed).toBe(3)
  })

  it('should compute group status as failed when any stage fails', () => {
    const stageStatuses = new Map<StageName, StageStatusEntry>([
      ['extraction', { status: 'complete', timestamp: new Date().toISOString() }],
      ['embedding', { status: 'failed', timestamp: new Date().toISOString() }],
      ['supervisor_routing', { status: 'pending', timestamp: new Date().toISOString() }],
    ])

    const { result } = renderHook(() => useStageGroups(stageStatuses))
    const coreWorkflowGroup = result.current[0]

    expect(coreWorkflowGroup.status.status).toBe('failed')
    expect(coreWorkflowGroup.status.failed).toBe(1)
  })

  it('should compute group status as partial when some stages complete and some skip', () => {
    const stageStatuses = new Map<StageName, StageStatusEntry>([
      ['tech_comparison', { status: 'complete', timestamp: new Date().toISOString() }],
      ['security_audit', { status: 'complete', timestamp: new Date().toISOString() }],
      ['implementation_planning', { status: 'skipped', timestamp: new Date().toISOString() }],
      ['performance_audit', { status: 'skipped', timestamp: new Date().toISOString() }],
      ['code_quality_audit', { status: 'skipped', timestamp: new Date().toISOString() }],
      ['trends_analysis', { status: 'skipped', timestamp: new Date().toISOString() }],
      ['dependencies_analysis', { status: 'skipped', timestamp: new Date().toISOString() }],
    ])

    const { result } = renderHook(() => useStageGroups(stageStatuses))
    const contentAnalysisGroup = result.current[1]

    expect(contentAnalysisGroup.status.status).toBe('partial')
    expect(contentAnalysisGroup.status.completed).toBe(2)
    expect(contentAnalysisGroup.status.skipped).toBe(5)
    expect(contentAnalysisGroup.status.progress).toBe(100) // Both completed and skipped count as done
  })

  it('should compute group status as completed when all stages are skipped', () => {
    const stageStatuses = new Map<StageName, StageStatusEntry>([
      ['tech_comparison', { status: 'skipped', timestamp: new Date().toISOString() }],
      ['security_audit', { status: 'skipped', timestamp: new Date().toISOString() }],
      ['implementation_planning', { status: 'skipped', timestamp: new Date().toISOString() }],
      ['performance_audit', { status: 'skipped', timestamp: new Date().toISOString() }],
      ['code_quality_audit', { status: 'skipped', timestamp: new Date().toISOString() }],
      ['trends_analysis', { status: 'skipped', timestamp: new Date().toISOString() }],
      ['dependencies_analysis', { status: 'skipped', timestamp: new Date().toISOString() }],
    ])

    const { result } = renderHook(() => useStageGroups(stageStatuses))
    const contentAnalysisGroup = result.current[1]

    expect(contentAnalysisGroup.status.status).toBe('completed')
    expect(contentAnalysisGroup.status.skipped).toBe(7)
    expect(contentAnalysisGroup.status.progress).toBe(100)
  })

  it('should compute progress percentage correctly', () => {
    const stageStatuses = new Map<StageName, StageStatusEntry>([
      ['extraction', { status: 'complete', timestamp: new Date().toISOString() }],
      ['embedding', { status: 'complete', timestamp: new Date().toISOString() }],
      ['supervisor_routing', { status: 'pending', timestamp: new Date().toISOString() }],
    ])

    const { result } = renderHook(() => useStageGroups(stageStatuses))
    const coreWorkflowGroup = result.current[0]

    // 2 out of 3 stages complete = 67%
    expect(coreWorkflowGroup.status.progress).toBe(67)
  })

  it('should include correct number of stages per group', () => {
    const stageStatuses = new Map<StageName, StageStatusEntry>()
    const { result } = renderHook(() => useStageGroups(stageStatuses))

    expect(result.current[0].status.total).toBe(3) // Core Workflow
    expect(result.current[1].status.total).toBe(7) // Content Analysis
    expect(result.current[2].status.total).toBe(4) // Tier 1
    expect(result.current[3].status.total).toBe(4) // Tier 2
    expect(result.current[4].status.total).toBe(4) // Tier 3
    expect(result.current[5].status.total).toBe(4) // Quality Pipeline
    expect(result.current[6].status.total).toBe(4) // Optional Stages
  })

  it('should handle extended statuses (synthesizing, detecting_conflicts)', () => {
    const stageStatuses = new Map<StageName, StageStatusEntry>([
      ['aggregation', { status: 'synthesizing', timestamp: new Date().toISOString() }],
      ['quality_gate', { status: 'pending', timestamp: new Date().toISOString() }],
      ['quality_validation', { status: 'pending', timestamp: new Date().toISOString() }],
      ['artifact_generation', { status: 'pending', timestamp: new Date().toISOString() }],
    ])

    const { result } = renderHook(() => useStageGroups(stageStatuses))
    const qualityPipelineGroup = result.current[5]

    expect(qualityPipelineGroup.status.status).toBe('in-progress')
    expect(qualityPipelineGroup.status.running).toBe(1)
  })

  it('should handle static_fallback as failed status', () => {
    const stageStatuses = new Map<StageName, StageStatusEntry>([
      ['aggregation', { status: 'static_fallback', timestamp: new Date().toISOString() }],
      ['quality_gate', { status: 'pending', timestamp: new Date().toISOString() }],
      ['quality_validation', { status: 'pending', timestamp: new Date().toISOString() }],
      ['artifact_generation', { status: 'pending', timestamp: new Date().toISOString() }],
    ])

    const { result } = renderHook(() => useStageGroups(stageStatuses))
    const qualityPipelineGroup = result.current[5]

    expect(qualityPipelineGroup.status.status).toBe('failed')
    expect(qualityPipelineGroup.status.failed).toBe(1)
  })
})
