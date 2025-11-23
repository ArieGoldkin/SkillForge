/**
 * SkillForge Design Tokens
 * Extracted from .superdesign/design_iterations/skillforge_theme_1.css
 *
 * Design System v1.0 - Clean Modern Design with Teal Accents
 * Color System: OKLCH (Perceptually uniform color space)
 */

// ============================================================================
// COLOR TOKENS (OKLCH)
// ============================================================================

/**
 * Light Theme Colors
 * Optimized for daylight viewing with teal accent
 */
export const lightColors = {
  background: 'oklch(0.9911 0 0)',
  foreground: 'oklch(0.2046 0 0)',
  card: 'oklch(0.9911 0 0)',
  cardForeground: 'oklch(0.2046 0 0)',
  popover: 'oklch(0.9911 0 0)',
  popoverForeground: 'oklch(0.4386 0 0)',
  primary: 'oklch(0.8348 0.1302 160.9080)', // Teal accent
  primaryForeground: 'oklch(0.2626 0.0147 166.4589)',
  secondary: 'oklch(0.9940 0 0)',
  secondaryForeground: 'oklch(0.2046 0 0)',
  muted: 'oklch(0.9461 0 0)',
  mutedForeground: 'oklch(0.2435 0 0)',
  accent: 'oklch(0.9461 0 0)',
  accentForeground: 'oklch(0.2435 0 0)',
  destructive: 'oklch(0.5523 0.1927 32.7272)',
  destructiveForeground: 'oklch(0.9934 0.0032 17.2118)',
  border: 'oklch(0.9037 0 0)',
  input: 'oklch(0.9731 0 0)',
  ring: 'oklch(0.8348 0.1302 160.9080)', // Teal focus ring

  // Chart colors
  chart1: 'oklch(0.8348 0.1302 160.9080)', // Teal
  chart2: 'oklch(0.6231 0.1880 259.8145)', // Purple
  chart3: 'oklch(0.6056 0.2189 292.7172)', // Magenta
  chart4: 'oklch(0.7686 0.1647 70.0804)', // Yellow-green
  chart5: 'oklch(0.6959 0.1491 162.4796)', // Green

  // Sidebar colors
  sidebar: 'oklch(0.9911 0 0)',
  sidebarForeground: 'oklch(0.5452 0 0)',
  sidebarPrimary: 'oklch(0.8348 0.1302 160.9080)',
  sidebarPrimaryForeground: 'oklch(0.2626 0.0147 166.4589)',
  sidebarAccent: 'oklch(0.9461 0 0)',
  sidebarAccentForeground: 'oklch(0.2435 0 0)',
  sidebarBorder: 'oklch(0.9037 0 0)',
  sidebarRing: 'oklch(0.8348 0.1302 160.9080)',
} as const

/**
 * Dark Theme Colors
 * Optimized for low-light viewing with enhanced teal accent
 */
export const darkColors = {
  background: 'oklch(0.1822 0 0)',
  foreground: 'oklch(0.9288 0.0126 255.5078)',
  card: 'oklch(0.2046 0 0)',
  cardForeground: 'oklch(0.9288 0.0126 255.5078)',
  popover: 'oklch(0.2603 0 0)',
  popoverForeground: 'oklch(0.7348 0 0)',
  primary: 'oklch(0.4365 0.1044 156.7556)', // Darker teal
  primaryForeground: 'oklch(0.9213 0.0135 167.1556)',
  secondary: 'oklch(0.2603 0 0)',
  secondaryForeground: 'oklch(0.9851 0 0)',
  muted: 'oklch(0.2393 0 0)',
  mutedForeground: 'oklch(0.7122 0 0)',
  accent: 'oklch(0.3132 0 0)',
  accentForeground: 'oklch(0.9851 0 0)',
  destructive: 'oklch(0.3123 0.0852 29.7877)',
  destructiveForeground: 'oklch(0.9368 0.0045 34.3092)',
  border: 'oklch(0.2809 0 0)',
  input: 'oklch(0.2603 0 0)',
  ring: 'oklch(0.8003 0.1821 151.7110)', // Bright teal focus ring

  // Chart colors
  chart1: 'oklch(0.8003 0.1821 151.7110)', // Bright teal
  chart2: 'oklch(0.7137 0.1434 254.6240)', // Purple
  chart3: 'oklch(0.7090 0.1592 293.5412)', // Magenta
  chart4: 'oklch(0.8369 0.1644 84.4286)', // Yellow
  chart5: 'oklch(0.7845 0.1325 181.9120)', // Green

  // Sidebar colors
  sidebar: 'oklch(0.1822 0 0)',
  sidebarForeground: 'oklch(0.6301 0 0)',
  sidebarPrimary: 'oklch(0.4365 0.1044 156.7556)',
  sidebarPrimaryForeground: 'oklch(0.9213 0.0135 167.1556)',
  sidebarAccent: 'oklch(0.3132 0 0)',
  sidebarAccentForeground: 'oklch(0.9851 0 0)',
  sidebarBorder: 'oklch(0.2809 0 0)',
  sidebarRing: 'oklch(0.8003 0.1821 151.7110)',
} as const

// ============================================================================
// TYPOGRAPHY TOKENS
// ============================================================================

/**
 * Font Families
 * Primary: Outfit (Google Fonts) - Modern, clean sans-serif
 */
export const fonts = {
  sans: 'Outfit, sans-serif',
  serif: 'ui-serif, Georgia, Cambria, "Times New Roman", Times, serif',
  mono: 'monospace',
} as const

/**
 * Font Sizes
 * Using rem units for accessibility
 */
export const fontSizes = {
  h1: '3rem', // 48px
  h2: '2rem', // 32px
  h3: '1.5rem', // 24px
  base: '1rem', // 16px
  sm: '0.875rem', // 14px
  xs: '0.75rem', // 12px
} as const

/**
 * Font Weights
 */
export const fontWeights = {
  normal: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
} as const

/**
 * Letter Spacing
 */
export const letterSpacing = {
  normal: '0.025em',
  tight: '-0.01em',
  wide: '0.05em',
} as const

/**
 * Line Heights
 */
export const lineHeights = {
  tight: 1.2,
  normal: 1.6,
  relaxed: 1.8,
} as const

// ============================================================================
// SPACING TOKENS
// ============================================================================

/**
 * Spacing Scale
 * Base unit: 0.25rem (4px)
 */
export const spacing = {
  0: '0',
  1: '0.25rem', // 4px
  2: '0.5rem', // 8px
  3: '0.75rem', // 12px
  4: '1rem', // 16px
  5: '1.25rem', // 20px
  6: '1.5rem', // 24px
  8: '2rem', // 32px
  10: '2.5rem', // 40px
  12: '3rem', // 48px
  16: '4rem', // 64px
  20: '5rem', // 80px
  24: '6rem', // 96px
} as const

// ============================================================================
// BORDER RADIUS TOKENS
// ============================================================================

/**
 * Border Radius Scale
 * Base: 0.5rem (8px)
 */
export const borderRadius = {
  none: '0',
  sm: 'calc(0.5rem - 4px)', // 4px
  md: 'calc(0.5rem - 2px)', // 6px
  lg: '0.5rem', // 8px
  xl: 'calc(0.5rem + 4px)', // 12px
  full: '9999px',
} as const

// ============================================================================
// SHADOW TOKENS
// ============================================================================

/**
 * Box Shadow Scale
 * Subtle shadows for depth perception
 */
export const shadows = {
  '2xs': '0px 1px 3px 0px hsl(0 0% 0% / 0.09)',
  xs: '0px 1px 3px 0px hsl(0 0% 0% / 0.09)',
  sm: '0px 1px 3px 0px hsl(0 0% 0% / 0.17), 0px 1px 2px -1px hsl(0 0% 0% / 0.17)',
  md: '0px 1px 3px 0px hsl(0 0% 0% / 0.17), 0px 2px 4px -1px hsl(0 0% 0% / 0.17)',
  lg: '0px 1px 3px 0px hsl(0 0% 0% / 0.17), 0px 4px 6px -1px hsl(0 0% 0% / 0.17)',
  xl: '0px 1px 3px 0px hsl(0 0% 0% / 0.17), 0px 8px 10px -1px hsl(0 0% 0% / 0.17)',
  '2xl': '0px 1px 3px 0px hsl(0 0% 0% / 0.43)',
} as const

// ============================================================================
// TYPE EXPORTS
// ============================================================================

export type LightColor = keyof typeof lightColors
export type DarkColor = keyof typeof darkColors
export type FontFamily = keyof typeof fonts
export type FontSize = keyof typeof fontSizes
export type FontWeight = keyof typeof fontWeights
export type LetterSpacing = keyof typeof letterSpacing
export type LineHeight = keyof typeof lineHeights
export type Spacing = keyof typeof spacing
export type BorderRadius = keyof typeof borderRadius
export type Shadow = keyof typeof shadows
