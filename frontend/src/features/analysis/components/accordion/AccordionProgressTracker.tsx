/* eslint-disable max-lines, max-lines-per-function -- Main orchestrator component with placeholder hooks and mobile components requires extended implementation for hierarchical accordion functionality */
/**
 * AccordionProgressTracker - Hierarchical Accordion-Based Progress Visualization
 *
 * Main orchestrator component that renders stage groups as collapsible accordions
 * with responsive behavior, MiniMap navigation, and mobile optimizations.
 *
 * Features:
 * - Hierarchical grouping of pipeline stages into logical categories
 * - Responsive accordion expansion limits (mobile: 1, tablet: 2, desktop: 3-5)
 * - Auto-expand active groups, auto-collapse inactive groups on mobile
 * - MiniMap navigation sidebar on desktop+ (tablet, laptop, desktop, ultrawide)
 * - Mobile FAB (Floating Action Button) for quick navigation
 * - Mobile bottom sheet for group selection on small screens
 * - Smooth expand/collapse animations via Framer Motion
 * - Activity feed integration (desktop+ only)
 *
 * @module features/analysis/components/accordion/AccordionProgressTracker
 */

import { memo, useCallback, useMemo, useRef, useState } from 'react'

import type { StageName } from '@app-types/sse'
import { AnimatePresence, motion } from 'framer-motion'

import { AgentActivityFeed } from '@/features/analysis/components/activity/AgentActivityFeed'
import type { StageStatusEntry } from '@/features/analysis/hooks/stageConfig'
import type { AgentActivity } from '@/features/analysis/hooks/useActivityFeed'
import { useBreakpoint } from '@/features/analysis/hooks/useBreakpoint'
import { useStageGroups } from '@/features/analysis/hooks/useStageGroups'
import type { AnalysisMode } from '@/features/analysis/types/accordion'

import { cn } from '@lib/utils'

import { StageItem } from '../progress/StageItem'

import { GroupHeader } from './GroupHeader'
import { MiniMap } from './MiniMap'
import type { MiniMapGroup } from './MiniMap'

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Success metrics for a stage (from useAnalysisProgress)
 */
export interface SuccessMetrics {
  findingsQuality?: 'high' | 'medium' | 'low'
  coverage?: 'comprehensive' | 'partial' | 'minimal'
  keyInsights?: string[]
}

/**
 * Props for AccordionProgressTracker
 */
export interface AccordionProgressTrackerProps {
  /** Map of stage statuses from useStageStatusProcessing */
  stageStatuses: Map<StageName, StageStatusEntry>
  /** Optional skip reasons from supervisor routing */
  skipReasons?: Record<string, string>
  /** Optional success metrics from agent completions */
  stageSuccessMetrics?: Map<string, SuccessMetrics>
  /** Analysis mode (quick, standard, deep) - determines active groups */
  analysisMode: AnalysisMode
  /** Optional agent activities for activity feed */
  activities?: AgentActivity[]
  /** Whether analysis is in progress (for live activity feed) */
  isLive?: boolean
  /** Optional className for wrapper */
  className?: string
}

// ============================================================================
// Helper: Detect active group (contains a running stage)
// ============================================================================

/**
 * Find the currently active group (contains a running stage)
 */
function findActiveGroupId(
  groups: ReturnType<typeof useStageGroups>,
  stageStatuses: Map<StageName, StageStatusEntry>
): string | null {
  for (const { group } of groups) {
    for (const stageName of group.stages) {
      const stageStatus = stageStatuses.get(stageName)
      if (stageStatus?.status === 'running' || stageStatus?.status === 'synthesizing') {
        return group.id
      }
    }
  }
  return null
}

/**
 * PLACEHOLDER: useAutoExpand hook
 *
 * TODO: Move to /Users/yonatangross/coding/SkillForge/frontend/src/features/analysis/hooks/useAutoExpand.ts
 *
 * Manages auto-expansion and auto-collapse of accordion groups based on:
 * - Active stage detection (expand group containing running stage)
 * - Breakpoint-based maxExpanded limits (mobile: 1, desktop: 5)
 * - User preferences (auto-expand enabled/disabled)
 */
function useAutoExpand(
  groups: Array<{ id: string; status: string; isActive: boolean }>,
  maxExpanded: number,
  _autoExpandEnabled: boolean = true
) {
  // PLACEHOLDER: Return basic state for now
  // Real implementation will:
  // 1. Track expandedGroups Set
  // 2. Auto-expand group with active stage
  // 3. Auto-collapse least-recently-used groups when exceeding maxExpanded
  // 4. Provide toggleGroup, expandAll, collapseAll actions
  // 5. Handle mobile auto-collapse on group change

  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set())

  const toggleGroup = useCallback(
    (groupId: string) => {
      setExpandedGroups((prev) => {
        const next = new Set(prev)
        if (next.has(groupId)) {
          next.delete(groupId)
        } else {
          // Enforce maxExpanded limit
          if (next.size >= maxExpanded) {
            // Remove oldest expanded group (first in set)
            const firstId = Array.from(next)[0]
            next.delete(firstId)
          }
          next.add(groupId)
        }
        return next
      })
    },
    [maxExpanded]
  )

  return {
    expandedGroups,
    toggleGroup,
    expandAll: () => setExpandedGroups(new Set(groups.map((g) => g.id))),
    collapseAll: () => setExpandedGroups(new Set()),
  }
}

// ============================================================================
// Placeholder Mobile Components (To be implemented)
// ============================================================================

/**
 * PLACEHOLDER: FloatingActionButton component
 *
 * TODO: Create /Users/yonatangross/coding/SkillForge/frontend/src/features/analysis/components/accordion/FloatingActionButton.tsx
 *
 * Mobile FAB for quick navigation and group controls
 */
const FloatingActionButton = memo(function FloatingActionButton({
  onClick,
}: {
  onClick: () => void
}) {
  // PLACEHOLDER: Simple button for now
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'fixed bottom-6 right-6 z-50',
        'w-14 h-14 rounded-full',
        'bg-primary text-primary-foreground',
        'shadow-lg hover:shadow-xl',
        'transition-all duration-200',
        'flex items-center justify-center'
      )}
      aria-label="Open navigation menu"
    >
      <svg
        className="w-6 h-6"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        role="img"
        aria-label="Menu icon"
      >
        <title>Menu</title>
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M4 6h16M4 12h16M4 18h16"
        />
      </svg>
    </button>
  )
})

/**
 * PLACEHOLDER: MobileBottomSheet component
 *
 * TODO: Create /Users/yonatangross/coding/SkillForge/frontend/src/features/analysis/components/accordion/MobileBottomSheet.tsx
 *
 * Mobile bottom sheet for group selection
 */
const MobileBottomSheet = memo(function MobileBottomSheet({
  isOpen,
  onClose,
  groups,
  onSelectGroup,
}: {
  isOpen: boolean
  onClose: () => void
  groups: MiniMapGroup[]
  onSelectGroup: (groupId: string) => void
}) {
  // PLACEHOLDER: Simple overlay for now
  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm"
      onClick={onClose}
      onKeyDown={(e) => {
        if (e.key === 'Escape') onClose()
      }}
      role="button"
      tabIndex={0}
      aria-label="Close navigation menu"
    >
      <div
        className="fixed bottom-0 left-0 right-0 bg-background border-t rounded-t-2xl p-6 max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <h2 className="text-lg font-semibold mb-4">Select Group</h2>
        <div className="space-y-2">
          {groups.map((group) => (
            <button
              key={group.id}
              type="button"
              onClick={() => {
                onSelectGroup(group.id)
                onClose()
              }}
              className="w-full p-3 text-left rounded-lg border hover:bg-muted transition-colors"
            >
              <div className="font-medium">{group.label}</div>
              <div className="text-sm text-muted-foreground">{group.progress}% complete</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
})

// ============================================================================
// Main Component
// ============================================================================

/**
 * AccordionProgressTracker - Main hierarchical progress visualization
 *
 * @example
 * ```tsx
 * <AccordionProgressTracker
 *   stageStatuses={stageStatuses}
 *   skipReasons={skipReasons}
 *   stageSuccessMetrics={stageSuccessMetrics}
 *   analysisMode="standard"
 *   activities={activities}
 *   isLive={!isComplete}
 * />
 * ```
 */
export const AccordionProgressTracker = memo(function AccordionProgressTracker({
  stageStatuses,
  skipReasons: _skipReasons,
  stageSuccessMetrics: _stageSuccessMetrics,
  analysisMode,
  activities = [],
  isLive = false,
  className,
}: AccordionProgressTrackerProps) {
  // ========================================================================
  // Responsive Breakpoint Detection
  // ========================================================================
  const { config, isMobile } = useBreakpoint()
  const { maxExpanded, showMiniMap, showActivityFeed } = config

  // ========================================================================
  // Stage Groups Computation
  // ========================================================================
  // Note: analysisMode can be used later to filter groups (e.g., Quick = fewer groups)
  const groups = useStageGroups(stageStatuses)

  // ========================================================================
  // Auto-Expand Management
  // ========================================================================
  const { expandedGroups, toggleGroup } = useAutoExpand(
    groups,
    maxExpanded,
    true // autoExpandEnabled
  )

  // ========================================================================
  // Mobile Bottom Sheet State
  // ========================================================================
  const [isMobileSheetOpen, setIsMobileSheetOpen] = useState(false)

  // ========================================================================
  // Active Group Detection
  // ========================================================================
  const activeGroupId = useMemo(() => {
    return findActiveGroupId(groups, stageStatuses)
  }, [groups, stageStatuses])

  // ========================================================================
  // MiniMap Data Transformation
  // ========================================================================
  const miniMapGroups: MiniMapGroup[] = useMemo(() => {
    return groups.map((g) => ({
      id: g.group.id,
      label: g.group.label,
      status: g.status.status,
      progress: g.status.progress,
      stagesCount: g.group.stages.length,
      description: g.group.description,
    }))
  }, [groups])

  // ========================================================================
  // Overall Progress Calculation
  // ========================================================================
  const overallProgress = useMemo(() => {
    if (groups.length === 0) return 0
    const totalProgress = groups.reduce((sum, g) => sum + g.status.progress, 0)
    return Math.round(totalProgress / groups.length)
  }, [groups])

  const overallStatus = useMemo(() => {
    const hasRunning = groups.some((g) => g.status.status === 'in-progress')
    const hasCompleted = groups.every((g) => g.status.status === 'completed')
    const hasFailed = groups.some(
      (g) => g.status.status === 'failed' || g.status.status === 'partial'
    )

    if (hasFailed) return 'failed' as const
    if (hasCompleted) return 'completed' as const
    if (hasRunning) return 'in-progress' as const
    return 'pending' as const
  }, [groups])

  // ========================================================================
  // Jump to Group Handler (for MiniMap)
  // ========================================================================
  const groupRefs = useRef<Map<string, HTMLDivElement>>(new Map())

  const handleJumpToGroup = useCallback(
    (groupId: string) => {
      const element = groupRefs.current.get(groupId)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' })
        // Expand the group if not already expanded
        if (!expandedGroups.has(groupId)) {
          toggleGroup(groupId)
        }
      }
    },
    [expandedGroups, toggleGroup]
  )

  // ========================================================================
  // Render
  // ========================================================================
  return (
    <div className={cn('flex gap-4', className)}>
      {/* Main Accordion Container */}
      <div className="flex-1 min-w-0">
        {/* Accordion List */}
        <div className="space-y-2" role="list" aria-label="Stage groups">
          {groups.map((groupedStage) => {
            const { group, status } = groupedStage
            const isCurrentlyExpanded = expandedGroups.has(group.id)

            return (
              <div
                key={group.id}
                ref={(el) => {
                  if (el) {
                    groupRefs.current.set(group.id, el)
                  } else {
                    groupRefs.current.delete(group.id)
                  }
                }}
                className="rounded-lg border border-border bg-background overflow-hidden"
                role="listitem"
              >
                {/* Group Header */}
                <GroupHeader
                  group={group}
                  status={status.status}
                  progress={status.progress}
                  isExpanded={isCurrentlyExpanded}
                  onToggle={() => toggleGroup(group.id)}
                  stagesCompleted={status.completed}
                  stagesTotal={status.total}
                />

                {/* Collapsible Stage List */}
                <AnimatePresence initial={false}>
                  {isCurrentlyExpanded && (
                    <motion.div
                      key={`content-${group.id}`}
                      id={`group-content-${group.id}`}
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{
                        duration: 0.3,
                        ease: [0.4, 0, 0.2, 1], // Tailwind's ease-out
                      }}
                      className="overflow-hidden"
                    >
                      <div className="p-4 space-y-2 border-t border-border bg-muted/20">
                        {group.stages.map((stageName, index) => {
                          const stageStatus = stageStatuses.get(stageName)
                          if (!stageStatus) return null

                          // Transform to StageState format expected by StageItem
                          const stageState = {
                            name: stageName,
                            label: stageName
                              .replace(/_/g, ' ')
                              .replace(/\b\w/g, (l) => l.toUpperCase()),
                            status: stageStatus.status,
                            agent: stageStatus.details?.agent_type as string | undefined,
                            error: stageStatus.details?.error as string | undefined,
                            errorCode: stageStatus.details?.error_code as string | undefined,
                          }

                          return (
                            <StageItem
                              key={stageName}
                              stage={stageState}
                              isLast={index === group.stages.length - 1}
                            />
                          )
                        })}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )
          })}
        </div>

        {/* Empty State */}
        {groups.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <p>No stage groups available for {analysisMode} mode.</p>
          </div>
        )}
      </div>

      {/* MiniMap Sidebar (Desktop+ only) */}
      {showMiniMap && !isMobile && (
        <MiniMap
          groups={miniMapGroups}
          activeGroupId={activeGroupId}
          onJumpToGroup={handleJumpToGroup}
          overallProgress={overallProgress}
          overallStatus={overallStatus}
        />
      )}

      {/* Activity Feed Sidebar (Desktop+ only) */}
      {showActivityFeed && !isMobile && activities.length > 0 && (
        <div className="w-[300px] shrink-0">
          <AgentActivityFeed activities={activities} isLive={isLive} maxItems={10} />
        </div>
      )}

      {/* Mobile FAB */}
      {isMobile && <FloatingActionButton onClick={() => setIsMobileSheetOpen(true)} />}

      {/* Mobile Bottom Sheet */}
      {isMobile && (
        <MobileBottomSheet
          isOpen={isMobileSheetOpen}
          onClose={() => setIsMobileSheetOpen(false)}
          groups={miniMapGroups}
          onSelectGroup={handleJumpToGroup}
        />
      )}
    </div>
  )
})

AccordionProgressTracker.displayName = 'AccordionProgressTracker'
