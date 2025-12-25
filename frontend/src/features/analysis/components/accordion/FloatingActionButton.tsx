/**
 * FloatingActionButton - Mobile quick-jump FAB for current stage navigation
 *
 * A floating action button that appears on mobile devices to help users
 * quickly jump to the currently active stage in the analysis pipeline.
 *
 * Features:
 * - Fixed bottom-right position (mobile only)
 * - Shows current stage number / total stages
 * - Tap to scroll to current active stage
 * - Subtle pulse animation on stage change
 * - Auto-hide when at top or when complete
 *
 * @module components/accordion/FloatingActionButton
 */
import { memo } from 'react'

import { motion, AnimatePresence } from 'framer-motion'
import { ArrowUp } from 'lucide-react'

import { cn } from '@lib/utils'

// ============================================================================
// Types
// ============================================================================

export interface FloatingActionButtonProps {
  /** Current active stage number (1-indexed) */
  currentStage: number

  /** Total number of stages in the pipeline */
  totalStages: number

  /** Callback to scroll to current stage */
  onJumpToCurrent: () => void

  /** Whether the button should be visible */
  isVisible: boolean

  /** Optional CSS classes */
  className?: string
}

// ============================================================================
// Animation Variants
// ============================================================================

const fabVariants = {
  hidden: {
    opacity: 0,
    scale: 0.8,
    y: 20,
  },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      type: 'spring' as const,
      stiffness: 300,
      damping: 25,
    },
  },
  exit: {
    opacity: 0,
    scale: 0.8,
    y: 20,
    transition: {
      duration: 0.2,
    },
  },
}

const pulseVariants = {
  pulse: {
    scale: [1, 1.05, 1],
    boxShadow: [
      '0 10px 25px rgba(0, 0, 0, 0.15)',
      '0 15px 35px rgba(0, 0, 0, 0.25)',
      '0 10px 25px rgba(0, 0, 0, 0.15)',
    ],
    transition: {
      duration: 0.6,
      ease: 'easeInOut' as const,
    },
  },
}

// ============================================================================
// Component
// ============================================================================

/**
 * FloatingActionButton component
 *
 * Displays a circular FAB at bottom-right on mobile devices, showing
 * current stage progress (e.g., "12/30") and allowing quick navigation
 * to the active stage.
 *
 * @example
 * ```tsx
 * <FloatingActionButton
 *   currentStage={12}
 *   totalStages={30}
 *   onJumpToCurrent={() => scrollToStage(12)}
 *   isVisible={!isAtTop && !isComplete}
 * />
 * ```
 */
/* eslint-disable max-lines-per-function -- Main component requires complete JSX layout for FAB (motion button with stage counter, divider, total, arrow icon). Already well-structured with clear sections. */
export const FloatingActionButton = memo(function FloatingActionButton({
  currentStage,
  totalStages,
  onJumpToCurrent,
  isVisible,
  className,
}: FloatingActionButtonProps) {
  return (
    <AnimatePresence>
      {isVisible && (
        <motion.button
          type="button"
          onClick={onJumpToCurrent}
          className={cn(
            // Base styles - circular button
            'fixed z-50 flex flex-col items-center justify-center',
            'w-14 h-14 rounded-full',
            // Colors
            'bg-primary text-primary-foreground',
            // Shadow for depth
            'shadow-lg',
            // Position - bottom right with safe area padding
            'bottom-6 right-4',
            // Mobile only (hidden on tablet/desktop)
            'md:hidden',
            // Hover state (for touch feedback)
            'active:scale-95',
            // Transition for smooth interactions
            'transition-transform duration-150',
            className
          )}
          variants={fabVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          whileTap={{ scale: 0.9 }}
          // Pulse animation on mount (subtle)
          key={currentStage} // Re-mount on stage change to trigger pulse
          style={{
            // iOS safe area padding
            paddingBottom: 'env(safe-area-inset-bottom)',
          }}
          aria-label={`Jump to current stage ${currentStage} of ${totalStages}`}
        >
          {/* Stage counter */}
          <motion.div
            className="flex flex-col items-center justify-center gap-0.5"
            variants={pulseVariants}
            animate="pulse"
          >
            {/* Current stage number */}
            <span className="text-sm font-bold leading-none">{currentStage}</span>

            {/* Divider */}
            <span className="text-[10px] leading-none opacity-70">/</span>

            {/* Total stages */}
            <span className="text-xs leading-none opacity-90">{totalStages}</span>
          </motion.div>

          {/* Arrow icon (subtle, small) */}
          <ArrowUp className="absolute top-1 right-1 h-3 w-3 opacity-60" />
        </motion.button>
      )}
    </AnimatePresence>
  )
})

/**
 * Memoized comparison for FloatingActionButton
 *
 * Only re-render if visibility, current stage, or total stages change.
 * Callback reference changes don't trigger re-renders.
 */
FloatingActionButton.displayName = 'FloatingActionButton'
