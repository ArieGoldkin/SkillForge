/**
 * useBreakpoint - Responsive breakpoint detection with window.matchMedia
 *
 * Provides efficient breakpoint detection and responsive configuration for
 * layout components. Uses window.matchMedia for performance and proper SSR handling.
 *
 * Breakpoints:
 * - mobile: 320-767px (touch-optimized, auto-collapse)
 * - tablet: 768-1023px (hybrid, limited expansion)
 * - laptop: 1024-1439px (standard desktop)
 * - desktop: 1440-2559px (wide screen, full features)
 * - ultrawide: 2560px+ (maximum expansion)
 *
 * Configuration per breakpoint:
 * - maxExpanded: Max number of accordion sections that can be open simultaneously
 * - autoCollapseDelay: Milliseconds before auto-collapse (0 = never)
 * - showMiniMap: Display stage mini-map navigation
 * - showActivityFeed: Display real-time activity feed
 * - touchOptimized: Enable touch-friendly interaction patterns
 *
 * @module hooks/useBreakpoint
 */
import { useEffect, useState } from 'react'

// ============================================================================
// Types
// ============================================================================

export type Breakpoint = 'mobile' | 'tablet' | 'laptop' | 'desktop' | 'ultrawide'

export interface BreakpointConfig {
  maxExpanded: number
  autoCollapseDelay: number
  showMiniMap: boolean
  showActivityFeed: boolean
  touchOptimized: boolean
}

export interface UseBreakpointResult {
  breakpoint: Breakpoint
  config: BreakpointConfig
  isMobile: boolean
  isTablet: boolean
  isLaptop: boolean
  isDesktop: boolean
  isUltrawide: boolean
}

// ============================================================================
// Breakpoint Media Queries
// ============================================================================

const BREAKPOINT_QUERIES = {
  mobile: '(max-width: 767px)',
  tablet: '(min-width: 768px) and (max-width: 1023px)',
  laptop: '(min-width: 1024px) and (max-width: 1439px)',
  desktop: '(min-width: 1440px) and (max-width: 2559px)',
  ultrawide: '(min-width: 2560px)',
} as const

// ============================================================================
// Breakpoint Configuration
// ============================================================================

const BREAKPOINT_CONFIGS: Record<Breakpoint, BreakpointConfig> = {
  mobile: {
    maxExpanded: 1, // Only one section open at a time
    autoCollapseDelay: 3000, // Auto-collapse after 3s to save screen space
    showMiniMap: false, // No mini-map on mobile
    showActivityFeed: false, // Hide activity feed on mobile
    touchOptimized: true, // Touch-friendly 44x44px tap targets
  },
  tablet: {
    maxExpanded: 2, // Two sections open simultaneously
    autoCollapseDelay: 5000, // Auto-collapse after 5s
    showMiniMap: true, // Show compact mini-map
    showActivityFeed: false, // Hide activity feed (save space)
    touchOptimized: true, // Still touch-friendly
  },
  laptop: {
    maxExpanded: 3, // Three sections open
    autoCollapseDelay: 0, // No auto-collapse
    showMiniMap: false, // Hide redundant mini-map (all groups visible on screen)
    showActivityFeed: true, // Show activity feed
    touchOptimized: false, // Mouse/keyboard optimized
  },
  desktop: {
    maxExpanded: 5, // Up to 5 sections open
    autoCollapseDelay: 0, // No auto-collapse
    showMiniMap: false, // Hide redundant mini-map (all groups visible on screen)
    showActivityFeed: true, // Full activity feed
    touchOptimized: false, // Mouse/keyboard optimized
  },
  ultrawide: {
    maxExpanded: 8, // All sections can be open
    autoCollapseDelay: 0, // No auto-collapse
    showMiniMap: false, // Hide redundant mini-map (all groups visible on screen)
    showActivityFeed: true, // Full activity feed with extended history
    touchOptimized: false, // Mouse/keyboard optimized
  },
}

// ============================================================================
// SSR-Safe Detection
// ============================================================================

/**
 * Detect current breakpoint using window.matchMedia
 * Returns 'desktop' as fallback for SSR (most common case)
 */
function detectBreakpoint(): Breakpoint {
  // SSR fallback - return desktop as default
  if (typeof window === 'undefined') {
    return 'desktop'
  }

  // Check each breakpoint in order (mobile first)
  if (window.matchMedia(BREAKPOINT_QUERIES.mobile).matches) {
    return 'mobile'
  }
  if (window.matchMedia(BREAKPOINT_QUERIES.tablet).matches) {
    return 'tablet'
  }
  if (window.matchMedia(BREAKPOINT_QUERIES.laptop).matches) {
    return 'laptop'
  }
  if (window.matchMedia(BREAKPOINT_QUERIES.ultrawide).matches) {
    return 'ultrawide'
  }

  // Default to desktop if no match
  return 'desktop'
}

// ============================================================================
// Main Hook
// ============================================================================

/**
 * Responsive breakpoint detection hook
 *
 * Uses window.matchMedia for efficient breakpoint detection with proper
 * event listener cleanup. Handles SSR gracefully with 'desktop' default.
 *
 * @returns Current breakpoint, configuration, and boolean flags
 *
 * @example
 * ```tsx
 * const { breakpoint, config, isMobile } = useBreakpoint()
 *
 * // Use breakpoint for conditional rendering
 * if (isMobile) {
 *   return <MobileLayout />
 * }
 *
 * // Use config for component behavior
 * <Accordion maxExpanded={config.maxExpanded} />
 * ```
 */
export function useBreakpoint(): UseBreakpointResult {
  // Initialize with detected breakpoint (SSR-safe)
  const [breakpoint, setBreakpoint] = useState<Breakpoint>(detectBreakpoint)

  useEffect(() => {
    // Skip if window is not available (SSR)
    if (typeof window === 'undefined') {
      return
    }

    // Create MediaQueryList objects for all breakpoints
    const mediaQueries: Record<Breakpoint, MediaQueryList> = {
      mobile: window.matchMedia(BREAKPOINT_QUERIES.mobile),
      tablet: window.matchMedia(BREAKPOINT_QUERIES.tablet),
      laptop: window.matchMedia(BREAKPOINT_QUERIES.laptop),
      desktop: window.matchMedia(BREAKPOINT_QUERIES.desktop),
      ultrawide: window.matchMedia(BREAKPOINT_QUERIES.ultrawide),
    }

    // Handler for media query changes
    const handleChange = () => {
      setBreakpoint(detectBreakpoint())
    }

    // Add event listeners to all media queries
    // Using 'change' event (modern browsers) with addEventListener
    for (const mq of Object.values(mediaQueries)) {
      mq.addEventListener('change', handleChange)
    }

    // Cleanup: Remove all event listeners on unmount
    return () => {
      for (const mq of Object.values(mediaQueries)) {
        mq.removeEventListener('change', handleChange)
      }
    }
  }, [])

  // Get configuration for current breakpoint
  const config = BREAKPOINT_CONFIGS[breakpoint]

  // Convenience boolean flags
  const isMobile = breakpoint === 'mobile'
  const isTablet = breakpoint === 'tablet'
  const isLaptop = breakpoint === 'laptop'
  const isDesktop = breakpoint === 'desktop'
  const isUltrawide = breakpoint === 'ultrawide'

  return {
    breakpoint,
    config,
    isMobile,
    isTablet,
    isLaptop,
    isDesktop,
    isUltrawide,
  }
}
