/**
 * Animation Constants and Utilities
 *
 * Standardized animation configuration for consistent transitions across components.
 * Based on framer-motion patterns and WCAG motion requirements.
 *
 * @module lib/animations
 */
/* eslint-disable max-lines -- Central animation utility file requires comprehensive constants, variants, and helpers for consistent animations across the UI */

import type { Transition, Variants } from 'framer-motion'

// ============================================================================
// Duration Constants
// ============================================================================

/**
 * Standard animation durations in seconds
 * Consistent timing creates a cohesive feel across the UI
 */
export const ANIMATION_DURATIONS = {
  /** Micro-interactions: tooltips, hover states (150ms) */
  fast: 0.15,
  /** Status changes, badge transitions (200ms) */
  normal: 0.2,
  /** Accordions, panel expansions (300ms) */
  slow: 0.3,
  /** Completion celebrations, hero animations (500ms) */
  celebration: 0.5,
} as const

// ============================================================================
// Easing Constants
// ============================================================================

/**
 * Standard easing curves for consistent motion feel
 */
export const ANIMATION_EASINGS = {
  /** Standard ease-out for most transitions */
  easeOut: [0.4, 0, 0.2, 1] as const,
  /** Ease-in-out for symmetric animations */
  easeInOut: [0.4, 0, 0.6, 1] as const,
  /** Spring-like bounce for celebratory moments */
  spring: { type: 'spring', stiffness: 300, damping: 25 } as const,
  /** Gentle spring for subtle feedback */
  gentleSpring: { type: 'spring', stiffness: 200, damping: 20 } as const,
} as const

// ============================================================================
// Transition Presets
// ============================================================================

/**
 * Pre-configured transition objects for common use cases
 */
export const TRANSITIONS = {
  /** Fast transition for micro-interactions */
  fast: {
    duration: ANIMATION_DURATIONS.fast,
    ease: ANIMATION_EASINGS.easeOut,
  } satisfies Transition,

  /** Normal transition for status changes */
  normal: {
    duration: ANIMATION_DURATIONS.normal,
    ease: ANIMATION_EASINGS.easeOut,
  } satisfies Transition,

  /** Slow transition for accordions */
  slow: {
    duration: ANIMATION_DURATIONS.slow,
    ease: ANIMATION_EASINGS.easeInOut,
  } satisfies Transition,

  /** Spring transition for playful animations */
  spring: {
    type: 'spring',
    stiffness: 300,
    damping: 25,
  } satisfies Transition,

  /** Celebration transition for completions */
  celebration: {
    type: 'spring',
    stiffness: 400,
    damping: 15,
  } satisfies Transition,
} as const

// ============================================================================
// Status Badge Animation Variants
// ============================================================================

/**
 * Animation variants for status badge transitions
 * Used with AnimatePresence for enter/exit animations
 */
export const statusBadgeVariants: Variants = {
  initial: {
    opacity: 0,
    scale: 0.8,
  },
  animate: {
    opacity: 1,
    scale: 1,
    transition: TRANSITIONS.normal,
  },
  exit: {
    opacity: 0,
    scale: 0.8,
    transition: TRANSITIONS.fast,
  },
}

/**
 * Animation variants for status icons
 * Includes rotation for visual interest
 */
export const statusIconVariants: Variants = {
  initial: {
    opacity: 0,
    scale: 0.5,
    rotate: -90,
  },
  animate: {
    opacity: 1,
    scale: 1,
    rotate: 0,
    transition: TRANSITIONS.spring,
  },
  exit: {
    opacity: 0,
    scale: 0.5,
    rotate: 90,
    transition: TRANSITIONS.fast,
  },
}

/**
 * Animation variants for completion celebrations
 * Extra bounce and scale for positive feedback
 */
export const celebrationVariants: Variants = {
  initial: {
    opacity: 0,
    scale: 0.3,
  },
  animate: {
    opacity: 1,
    scale: 1,
    transition: TRANSITIONS.celebration,
  },
  exit: {
    opacity: 0,
    scale: 0.8,
    transition: TRANSITIONS.normal,
  },
}

/**
 * Animation variants for error states
 * Subtle shake effect for attention
 */
export const errorVariants: Variants = {
  initial: {
    opacity: 0,
    x: -10,
  },
  animate: {
    opacity: 1,
    x: 0,
    transition: TRANSITIONS.normal,
  },
  exit: {
    opacity: 0,
    x: 10,
    transition: TRANSITIONS.fast,
  },
}

/**
 * Animation variants for slide-in content
 * Used for agent info, additional details
 */
export const slideInVariants: Variants = {
  initial: {
    opacity: 0,
    x: -8,
    height: 0,
  },
  animate: {
    opacity: 1,
    x: 0,
    height: 'auto',
    transition: TRANSITIONS.normal,
  },
  exit: {
    opacity: 0,
    x: -8,
    height: 0,
    transition: TRANSITIONS.fast,
  },
}

/**
 * Animation variants for fade content
 * Simple opacity transition for subtle changes
 */
export const fadeVariants: Variants = {
  initial: {
    opacity: 0,
  },
  animate: {
    opacity: 1,
    transition: TRANSITIONS.normal,
  },
  exit: {
    opacity: 0,
    transition: TRANSITIONS.fast,
  },
}

// ============================================================================
// Stagger Utilities
// ============================================================================

/**
 * Create stagger transition for lists
 * @param index - Item index in the list
 * @param baseDelay - Initial delay before stagger starts (default: 0)
 * @param staggerDelay - Delay between each item (default: 0.05)
 */
export function getStaggerDelay(
  index: number,
  baseDelay: number = 0,
  staggerDelay: number = 0.05
): number {
  return baseDelay + index * staggerDelay
}

/**
 * Create stagger variants for container
 */
export const staggerContainerVariants: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1,
    },
  },
}

/**
 * Create stagger variants for children items
 */
export const staggerItemVariants: Variants = {
  initial: {
    opacity: 0,
    y: 10,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: TRANSITIONS.normal,
  },
}

// ============================================================================
// CSS Color Values for Animation
// ============================================================================

/**
 * OKLCH color values for status colors
 * Required for framer-motion color interpolation (can't use Tailwind classes)
 */
export const STATUS_COLORS = {
  complete: {
    bg: 'oklch(0.6959 0.1491 162.4796)',
    border: 'oklch(0.5959 0.1691 162.4796)',
    text: '#ffffff',
  },
  running: {
    bg: 'oklch(0.6232 0.2118 259.1492)',
    border: 'oklch(0.5232 0.2318 259.1492)',
    text: '#ffffff',
  },
  failed: {
    bg: 'oklch(0.6369 0.2077 25.3313)',
    border: 'oklch(0.5369 0.2277 25.3313)',
    text: '#ffffff',
  },
  skipped: {
    bg: 'oklch(0.5556 0.0001 286.3746 / 0.5)',
    border: 'oklch(0.5556 0.0001 286.3746 / 0.3)',
    text: 'var(--muted-foreground)',
  },
  pending: {
    bg: 'oklch(0.5556 0.0001 286.3746 / 0.2)',
    border: 'oklch(0.5556 0.0001 286.3746 / 0.2)',
    text: 'var(--muted-foreground)',
  },
} as const

export type StatusColorKey = keyof typeof STATUS_COLORS
