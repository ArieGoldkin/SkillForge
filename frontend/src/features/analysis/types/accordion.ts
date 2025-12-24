/**
 * Type definitions for Hierarchical Accordion Progress Tracker
 *
 * This file defines all TypeScript interfaces for the hierarchical grouping
 * of pipeline stages into collapsible accordion groups with responsive behavior.
 *
 * @module features/analysis/types/accordion
 */

import type { LucideIcon } from 'lucide-react'

import type { StageName } from '@/schemas/base'

// ============================================================================
// Core Group Types
// ============================================================================

/**
 * Status of a stage group (derived from member stages)
 * - pending: No stages started yet
 * - in-progress: At least one stage is running
 * - completed: All stages completed successfully
 * - failed: At least one stage failed (terminal failure)
 * - partial: Some stages completed, some skipped/failed (non-terminal)
 */
export type GroupStatus = 'pending' | 'in-progress' | 'completed' | 'failed' | 'partial'

/**
 * Analysis mode that determines which groups are active
 * - quick: Tier 1 Universal agents only
 * - standard: Tier 1 + Tier 2 Validation agents
 * - deep: All tiers (1 + 2 + 3 Research agents)
 */
export type AnalysisMode = 'quick' | 'standard' | 'deep'

/**
 * Stage group configuration
 * Groups related pipeline stages under a collapsible accordion
 */
export interface StageGroup {
  /** Unique group identifier */
  id: string
  /** Display label for the group header */
  label: string
  /** Icon component from lucide-react */
  icon: LucideIcon
  /** Stages that belong to this group */
  stages: StageName[]
  /** Optional description shown in group header or tooltip */
  description?: string
  /** Analysis modes where this group is active (undefined = all modes) */
  modes?: AnalysisMode[]
  /** Whether this group is optional (all stages can be skipped) */
  optional?: boolean
}

// ============================================================================
// Accordion State Management
// ============================================================================

/**
 * Accordion UI state
 * Tracks which groups are expanded and UI interaction settings
 */
export interface AccordionState {
  /** Set of expanded group IDs */
  expandedGroups: Set<string>
  /** Currently active stage name (if any) */
  activeStage: StageName | null
  /** Whether to auto-expand groups when their first stage starts */
  autoExpandEnabled: boolean
  /** Whether to auto-collapse inactive groups on mobile */
  autoCollapseInactive: boolean
}

/**
 * Accordion state actions (for reducer pattern)
 */
export type AccordionAction =
  | { type: 'EXPAND_GROUP'; groupId: string }
  | { type: 'COLLAPSE_GROUP'; groupId: string }
  | { type: 'TOGGLE_GROUP'; groupId: string }
  | { type: 'EXPAND_ALL' }
  | { type: 'COLLAPSE_ALL' }
  | { type: 'SET_ACTIVE_STAGE'; stage: StageName | null }
  | { type: 'TOGGLE_AUTO_EXPAND' }
  | { type: 'TOGGLE_AUTO_COLLAPSE' }
  | { type: 'AUTO_EXPAND_FOR_STAGE'; stage: StageName }
  | { type: 'AUTO_COLLAPSE_INACTIVE'; activeGroupId: string }

// ============================================================================
// Responsive Behavior
// ============================================================================

/**
 * Responsive breakpoint names
 * Maps to Tailwind breakpoints in our design system
 */
export type ResponsiveBreakpoint = 'mobile' | 'tablet' | 'laptop' | 'desktop' | 'ultrawide'

/**
 * Breakpoint-specific configuration
 * Controls how many groups can be expanded simultaneously and UI density
 */
export interface BreakpointConfig {
  /** Maximum number of groups that can be expanded simultaneously */
  maxExpanded: number
  /** Auto-collapse delay in ms when exceeding maxExpanded (0 = immediate) */
  autoCollapseDelay: number
  /** Whether to show the mini-map navigation aid */
  showMiniMap: boolean
  /** Whether to show the activity feed sidebar */
  showActivityFeed: boolean
  /** Default collapsed state for inactive groups */
  defaultCollapsed: boolean
}

/**
 * Responsive configuration map
 * Defines behavior for each breakpoint
 */
export type ResponsiveConfig = Record<ResponsiveBreakpoint, BreakpointConfig>

// ============================================================================
// Group Status Computation
// ============================================================================

/**
 * Stage status count (for group status derivation)
 */
export interface StageStatusCount {
  pending: number
  running: number
  complete: number
  failed: number
  skipped: number
}

/**
 * Group status metadata (for debugging and tooltips)
 */
export interface GroupStatusMeta {
  /** Computed group status */
  status: GroupStatus
  /** Number of completed stages */
  completed: number
  /** Total number of stages in group */
  total: number
  /** Number of failed stages */
  failed: number
  /** Number of skipped stages */
  skipped: number
  /** Number of running stages */
  running: number
  /** Progress percentage (0-100) */
  progress: number
}

// ============================================================================
// Analytics & Events
// ============================================================================

/**
 * Accordion interaction event (for analytics)
 */
export interface AccordionEvent {
  /** Event type */
  type: 'expand' | 'collapse' | 'auto-expand' | 'auto-collapse' | 'toggle'
  /** Group ID affected */
  groupId: string
  /** Timestamp */
  timestamp: number
  /** Current breakpoint when event occurred */
  breakpoint: ResponsiveBreakpoint
  /** Whether action was user-initiated or automatic */
  userInitiated: boolean
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * Grouped stages view (helper for rendering)
 */
export interface GroupedStages {
  /** The group configuration */
  group: StageGroup
  /** Computed group status */
  status: GroupStatusMeta
  /** Whether this group is currently expanded */
  isExpanded: boolean
  /** Whether this group contains the active stage */
  isActive: boolean
}
