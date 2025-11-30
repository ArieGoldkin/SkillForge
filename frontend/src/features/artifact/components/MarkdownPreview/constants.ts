import { FileText, Sparkles, Zap } from 'lucide-react'

/**
 * Language color configuration for code block language dots
 */
export const LANGUAGE_COLORS: Record<string, string> = {
  typescript: 'oklch(0.6231 0.1880 259.8145)', // Blue
  javascript: 'oklch(0.7686 0.1647 70.0804)', // Yellow
  python: 'oklch(0.6231 0.1880 259.8145)', // Blue
  bash: 'oklch(0.6056 0.2189 292.7172)', // Purple
  json: 'oklch(0.7686 0.1647 142.4953)', // Green
  markdown: 'oklch(0.6959 0.1491 162.4796)', // Teal
  default: 'var(--primary)',
}

/**
 * Complexity icon mapping
 */
export const COMPLEXITY_ICONS = {
  simple: Sparkles,
  intermediate: FileText,
  advanced: Zap,
} as const

/**
 * Complexity color mapping (OKLCH values)
 */
export const COMPLEXITY_COLORS = {
  simple: 'oklch(0.7686 0.1647 142.4953)', // Green
  intermediate: 'oklch(0.7686 0.1647 70.0804)', // Yellow
  advanced: 'oklch(0.6056 0.2189 292.7172)', // Purple
} as const
