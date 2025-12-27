/**
 * Stage Status Configuration
 * Enum-driven config pattern for stage status display (icons, badges, labels)
 *
 * This file provides exhaustively-typed configuration using `satisfies Record<>`
 * to ensure all StageStatus values are handled at compile time.
 *
 * Shared by:
 * - AccordionStageItem.tsx (accordion layout)
 * - StageItem.tsx (progress timeline layout)
 *
 * NOTE: This file uses .tsx extension because it contains JSX (icon renderers).
 * The react-refresh warnings are disabled because this is a config file, not a component.
 *
 * @module features/analysis/config/stageStatusConfig
 */

/* eslint-disable react-refresh/only-export-components -- Config file with JSX icon renderers */

import type React from 'react'

import { CheckCircle2, Circle, Loader2, MinusCircle, XCircle } from 'lucide-react'

import type { StageStatus } from '@/schemas/sse'

import { cn } from '@lib/utils'

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Configuration for each stage status
 */
export interface StageStatusConfig {
  /** Display label */
  label: string
  /** Badge variant */
  badgeVariant: 'default' | 'success' | 'warning' | 'destructive' | 'secondary'
  /** Icon renderer function - receives icon size class */
  icon: (iconClasses: string) => React.ReactNode
}

// ============================================================================
// Status Configuration Map
// ============================================================================

/**
 * Exhaustive configuration for all stage statuses
 *
 * Using `satisfies Record<StageStatus, ...>` ensures:
 * 1. All StageStatus values MUST be present
 * 2. No extra keys can be added
 * 3. TypeScript will error if a new status is added to StageStatus enum
 *
 * This replaces switch statements with a lookup table pattern.
 */
export const STAGE_STATUS_CONFIG = {
  complete: {
    label: 'Complete',
    badgeVariant: 'success',
    icon: (iconClasses: string) => (
      <CheckCircle2 className={cn(iconClasses, 'text-status-success')} aria-hidden="true" />
    ),
  },
  running: {
    label: 'Running',
    badgeVariant: 'warning',
    icon: (iconClasses: string) => (
      <Loader2 className={cn(iconClasses, 'animate-spin text-status-warning')} aria-hidden="true" />
    ),
  },
  synthesizing: {
    label: 'Synthesizing',
    badgeVariant: 'warning',
    icon: (iconClasses: string) => (
      <Loader2 className={cn(iconClasses, 'animate-spin text-status-warning')} aria-hidden="true" />
    ),
  },
  detecting_conflicts: {
    label: 'Detecting Conflicts',
    badgeVariant: 'warning',
    icon: (iconClasses: string) => (
      <Loader2 className={cn(iconClasses, 'animate-spin text-status-warning')} aria-hidden="true" />
    ),
  },
  failed: {
    label: 'Failed',
    badgeVariant: 'destructive',
    icon: (iconClasses: string) => (
      <XCircle className={cn(iconClasses, 'text-status-error')} aria-hidden="true" />
    ),
  },
  static_fallback: {
    label: 'Static Fallback',
    badgeVariant: 'destructive',
    icon: (iconClasses: string) => (
      <XCircle className={cn(iconClasses, 'text-status-error')} aria-hidden="true" />
    ),
  },
  skipped: {
    label: 'Skipped',
    badgeVariant: 'secondary',
    icon: (iconClasses: string) => (
      <MinusCircle className={cn(iconClasses, 'text-muted-foreground')} aria-hidden="true" />
    ),
  },
  pending: {
    label: 'Pending',
    badgeVariant: 'default',
    icon: (iconClasses: string) => (
      <Circle className={cn(iconClasses, 'text-muted-foreground')} aria-hidden="true" />
    ),
  },
} satisfies Record<StageStatus, StageStatusConfig>

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get status icon component for a stage
 * @param status - Stage status
 * @param iconClasses - CSS classes for icon sizing/styling
 */
export function getStatusIcon(status: StageStatus, iconClasses: string): React.ReactNode {
  return STAGE_STATUS_CONFIG[status].icon(iconClasses)
}

/**
 * Get badge variant for stage status
 * @param status - Stage status
 */
export function getStatusBadgeVariant(
  status: StageStatus
): 'default' | 'success' | 'warning' | 'destructive' | 'secondary' {
  return STAGE_STATUS_CONFIG[status].badgeVariant
}

/**
 * Format status for display
 * @param status - Stage status
 */
export function formatStatus(status: StageStatus): string {
  return STAGE_STATUS_CONFIG[status].label
}

/**
 * Format agent name from snake_case to Title Case
 * @param agent - Agent name in snake_case
 */
export function formatAgentName(agent: string): string {
  return agent
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}
