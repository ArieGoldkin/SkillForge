/**
 * URL helper utilities for artifact display
 *
 * Provides utilities to detect and handle golden dataset URLs
 */

/**
 * Check if a URL is from the golden dataset fixture
 * Golden dataset URLs use the fake domain: docs.skillforge.dev
 */
export const isGoldenDatasetUrl = (url: string | null | undefined): boolean => {
  if (!url) return false
  return url.includes('docs.skillforge.dev')
}

/**
 * Extract document name from golden dataset URL
 * @example
 * extractDocumentName('https://docs.skillforge.dev/chain-of-thought')
 * // Returns: 'Chain Of Thought'
 */
export const extractDocumentName = (url: string): string => {
  try {
    const urlObj = new URL(url)
    // Remove trailing slash and get path segments
    const pathname = urlObj.pathname.replace(/\/$/, '')
    const segments = pathname.split('/').filter(Boolean)
    const docId = segments[segments.length - 1]

    // Return fallback if no document ID found
    if (!docId) {
      return 'Example Document'
    }

    // Convert kebab-case to Title Case
    return docId
      .split('-')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  } catch {
    return 'Example Document'
  }
}

/**
 * Get display information for source URL
 * Shows badge for golden dataset, actual URL for real sources
 */
export const getSourceUrlDisplay = (
  url: string | null | undefined
): {
  isGoldenDataset: boolean
  displayText: string
  badgeText?: string
} => {
  if (!url) {
    return { isGoldenDataset: false, displayText: 'Unknown source' }
  }

  if (isGoldenDatasetUrl(url)) {
    return {
      isGoldenDataset: true,
      displayText: extractDocumentName(url),
      badgeText: '📚 Golden Dataset',
    }
  }

  return { isGoldenDataset: false, displayText: url }
}
