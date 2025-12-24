/**
 * Base Zod Schemas for SkillForge
 * Defines core enum types used across SSE events and API responses
 *
 * @module schemas/base
 */

import { z } from 'zod'

/**
 * Stage status values
 * - pending: Stage hasn't started yet
 * - running: Stage is currently executing
 * - complete: Stage finished successfully
 * - failed: Stage encountered an error
 * - skipped: Stage was skipped (not selected by supervisor)
 * - synthesizing: Aggregation stage is synthesizing findings
 * - detecting_conflicts: Aggregation stage detecting conflicts
 * - static_fallback: Using static fallback due to errors
 */
export const StageStatusSchema = z.enum([
  'pending',
  'running',
  'complete',
  'failed',
  'skipped',
  // Extended statuses for aggregation stage
  'synthesizing',
  'detecting_conflicts',
  'static_fallback',
])

/**
 * Agent stage names - represent individual processing stages
 * These match backend stage names from AGENT_REGISTRY (backend/app/core/agent_config.py)
 *
 * Backend sends these exact stage names via SSE events.
 * DO NOT add backwards-compatible aliases - this is FORWARD-ONLY.
 */
export const AgentStageNameSchema = z.enum([
  // Core workflow stages (always present)
  'extraction',
  'embedding',
  'supervisor_routing',
  'aggregation',
  'artifact_generation',
  // Content-based agent stages (dynamically selected by supervisor, 0-7 agents)
  'tech_comparison',
  'security_audit',
  'implementation_planning', // Used by BOTH implementation_planner AND integration_feasibility
  'performance_audit',
  'code_quality_audit',
  'trends_analysis',
  'dependencies_analysis',
  // Tier 1: Universal agents (always run in Quick+ mode)
  'key_insights',
  'pros_cons',
  'audience_fit',
  'actionable',
  // Tier 2: Validation agents (run in Standard+ mode)
  'fact_validation',
  'source_credibility',
  'freshness_check',
  'alternatives_finding',
  // Tier 3: Research agents (run in Deep Dive mode)
  'deep_research',
  'community_pulse',
  'knowledge_curation',
  'learning_path',
  // Optional stages
  'chunking', // Only if ENABLE_COARSE_TO_FINE=true
  // Quality gate stages (emitted during quality validation)
  'quality_gate',
  'quality_validation',
])

/**
 * Workflow-level stage names - represent workflow-wide events
 */
export const WorkflowStageNameSchema = z.enum(['workflow', 'pattern_comparison', 'metrics'])

/**
 * All possible stage names (agent + workflow-level)
 */
export const StageNameSchema = z.union([AgentStageNameSchema, WorkflowStageNameSchema])

/**
 * Content type for analyzed resources
 */
export const ContentTypeSchema = z.enum(['article', 'video', 'repo'])

/**
 * Findings quality level
 */
export const FindingsQualitySchema = z.enum(['high', 'medium', 'low'])

/**
 * Coverage level for analysis
 */
export const CoverageSchema = z.enum(['comprehensive', 'partial', 'minimal'])

// ============================================================================
// Type Inference - Export TypeScript types from Zod schemas
// ============================================================================

export type StageStatus = z.infer<typeof StageStatusSchema>
export type AgentStageName = z.infer<typeof AgentStageNameSchema>
export type WorkflowStageName = z.infer<typeof WorkflowStageNameSchema>
export type StageName = z.infer<typeof StageNameSchema>
export type ContentType = z.infer<typeof ContentTypeSchema>
export type FindingsQuality = z.infer<typeof FindingsQualitySchema>
export type Coverage = z.infer<typeof CoverageSchema>
