/**
 * MobileBottomSheet - Sliding drawer for mobile stage details
 *
 * A mobile-optimized bottom sheet that slides up from the bottom of the screen
 * to display detailed stage information for a selected group. Features drag-to-dismiss,
 * backdrop overlay, safe area support, and smooth animations.
 *
 * @module features/analysis/components/accordion/MobileBottomSheet
 */
/* eslint-disable max-lines -- Bottom sheet component requires comprehensive implementation with keyboard handling, focus trap, drag gestures, body scroll lock, and complete JSX structure. All sections are well-organized and necessary. */
import * as React from 'react'

import { X } from 'lucide-react'
import { createPortal } from 'react-dom'

import { cn } from '@lib/utils'

import type { StageGroup } from '../../types/accordion'
import type { AnalysisStep } from '../steps/AnalysisStepList'
import { AnalysisStepList } from '../steps/AnalysisStepList'

// ============================================================================
// Types
// ============================================================================

export interface MobileBottomSheetProps {
  /** Whether the sheet is open */
  isOpen: boolean
  /** Callback when the sheet should close */
  onClose: () => void
  /** The selected stage group */
  group: StageGroup | null
  /** Stages to display in the sheet */
  stages: AnalysisStep[]
  /** Sheet title (overrides group label if provided) */
  title?: string
}

// ============================================================================
// Constants
// ============================================================================

const DRAG_THRESHOLD = 100 // px - Distance to drag before dismissing
const SAFE_AREA_BOTTOM = 'max(env(safe-area-inset-bottom), 1rem)' // iOS safe area

// ============================================================================
// Component
// ============================================================================

/**
 * MobileBottomSheet - Draggable bottom sheet for mobile stage details
 *
 * Features:
 * - Slides up from bottom with spring animation
 * - Drag-to-dismiss gesture (swipe down)
 * - Backdrop overlay with click-to-close
 * - Respects iOS safe area insets
 * - Maximum 80vh height with scroll
 * - Focus trap when open
 * - Close on Escape key
 *
 * @example
 * ```tsx
 * <MobileBottomSheet
 *   isOpen={selectedGroup !== null}
 *   onClose={() => setSelectedGroup(null)}
 *   group={selectedGroup}
 *   stages={filteredStages}
 *   title="Content Extraction"
 * />
 * ```
 */
/* eslint-disable max-lines-per-function -- Component requires complete JSX layout for bottom sheet (backdrop overlay, drag handle, header with icon/title/close button, scrollable content area with stage list). Multiple effect hooks for keyboard handling, focus trap, drag gestures, and body scroll lock. Well-structured with clear sections. */
export function MobileBottomSheet({
  isOpen,
  onClose,
  group,
  stages,
  title,
}: MobileBottomSheetProps): React.ReactPortal | null {
  const sheetRef = React.useRef<HTMLDivElement>(null)
  const dragStartY = React.useRef<number>(0)
  const dragCurrentY = React.useRef<number>(0)
  const [isDragging, setIsDragging] = React.useState(false)
  const [translateY, setTranslateY] = React.useState(0)

  // ============================================================================
  // Keyboard Handling
  // ============================================================================

  React.useEffect(() => {
    if (!isOpen) return

    const handleEscape = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen, onClose])

  // ============================================================================
  // Focus Trap
  // ============================================================================

  React.useEffect(() => {
    if (!isOpen || !sheetRef.current) return

    const sheet = sheetRef.current
    const focusableElements = sheet.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
    const firstElement = focusableElements[0]
    const lastElement = focusableElements[focusableElements.length - 1]

    const handleTab = (e: KeyboardEvent): void => {
      if (e.key !== 'Tab') return

      if (e.shiftKey) {
        // Shift+Tab - focus last if currently on first
        if (document.activeElement === firstElement) {
          e.preventDefault()
          lastElement?.focus()
        }
      } else {
        // Tab - focus first if currently on last
        if (document.activeElement === lastElement) {
          e.preventDefault()
          firstElement?.focus()
        }
      }
    }

    sheet.addEventListener('keydown', handleTab)
    firstElement?.focus()

    return () => {
      sheet.removeEventListener('keydown', handleTab)
    }
  }, [isOpen])

  // ============================================================================
  // Drag Gesture Handling
  // ============================================================================

  const handleDragStart = (e: React.TouchEvent | React.MouseEvent): void => {
    const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
    dragStartY.current = clientY
    dragCurrentY.current = clientY
    setIsDragging(true)
  }

  const handleDragMove = (e: React.TouchEvent | React.MouseEvent): void => {
    if (!isDragging) return

    const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
    dragCurrentY.current = clientY
    const deltaY = clientY - dragStartY.current

    // Only allow dragging down (positive deltaY)
    if (deltaY > 0) {
      setTranslateY(deltaY)
    }
  }

  const handleDragEnd = (): void => {
    if (!isDragging) return

    const deltaY = dragCurrentY.current - dragStartY.current

    // Close if dragged beyond threshold
    if (deltaY > DRAG_THRESHOLD) {
      onClose()
    }

    // Reset drag state
    setIsDragging(false)
    setTranslateY(0)
    dragStartY.current = 0
    dragCurrentY.current = 0
  }

  // ============================================================================
  // Body Scroll Lock
  // ============================================================================

  React.useEffect(() => {
    if (isOpen) {
      // Prevent body scroll when sheet is open
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }

    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  // ============================================================================
  // Render
  // ============================================================================

  if (!isOpen || !group) {
    return null
  }

  const sheetTitle = title || group.label
  const GroupIcon = group.icon

  return createPortal(
    <div
      className="fixed inset-0 z-50 md:hidden"
      role="dialog"
      aria-modal="true"
      aria-labelledby="bottom-sheet-title"
    >
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 bg-black/80 transition-opacity duration-300',
          isOpen ? 'opacity-100' : 'opacity-0'
        )}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sheet */}
      <div
        ref={sheetRef}
        className={cn(
          'fixed bottom-0 left-0 right-0 z-50',
          'max-h-[80vh] rounded-t-2xl border-t bg-background shadow-2xl',
          'transition-transform duration-300 ease-out',
          isOpen ? 'translate-y-0' : 'translate-y-full',
          isDragging && 'transition-none'
        )}
        style={{
          transform: isDragging ? `translateY(${translateY}px)` : undefined,
          paddingBottom: SAFE_AREA_BOTTOM,
        }}
      >
        {/* Drag Handle */}
        <div
          role="button"
          tabIndex={0}
          className="flex cursor-grab touch-none items-center justify-center py-3 active:cursor-grabbing"
          onTouchStart={handleDragStart}
          onTouchMove={handleDragMove}
          onTouchEnd={handleDragEnd}
          onMouseDown={handleDragStart}
          onMouseMove={handleDragMove}
          onMouseUp={handleDragEnd}
          onMouseLeave={handleDragEnd}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              onClose()
            }
          }}
          aria-label="Drag to close or press Enter"
        >
          <div className="h-1.5 w-12 rounded-full bg-muted-foreground/40" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 pb-4">
          <div className="flex items-center gap-3">
            <GroupIcon className="h-5 w-5 text-primary" aria-hidden="true" />
            <h2
              id="bottom-sheet-title"
              className="text-lg font-semibold leading-none tracking-tight"
            >
              {sheetTitle}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className={cn(
              'rounded-sm p-1.5 opacity-70 transition-opacity hover:opacity-100',
              'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2'
            )}
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content - Scrollable */}
        <div className="overflow-y-auto px-6 py-4" style={{ maxHeight: 'calc(80vh - 8rem)' }}>
          {group.description && (
            <p className="mb-4 text-sm text-muted-foreground">{group.description}</p>
          )}
          <AnalysisStepList steps={stages} />
        </div>
      </div>
    </div>,
    document.body
  )
}
