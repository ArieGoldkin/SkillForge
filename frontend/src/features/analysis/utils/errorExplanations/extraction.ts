/**
 * Extraction-related error explanations
 */
import type { ErrorExplanation } from './types'

export const EXTRACTION_ERRORS: Record<string, ErrorExplanation> = {
  HTTP_404: {
    title: 'Page Not Found',
    reason: 'The URL you provided could not be found (404 error)',
    action: 'Check the URL and try again, or the page may have been removed',
    retryable: true,
    severity: 'critical',
  },
  HTTP_5XX: {
    title: 'Server Error',
    reason: 'The website server returned an error (5xx status code)',
    action: 'The website may be temporarily down. Try again in a few minutes',
    retryable: true,
    severity: 'critical',
  },
  TIMEOUT: {
    title: 'Request Timeout',
    reason: 'The request took too long to complete',
    action: 'The website may be slow. Try again or check your internet connection',
    retryable: true,
    severity: 'critical',
  },
  ERROR_PAGE: {
    title: 'Error Page Detected',
    reason: 'The website returned an error page instead of content',
    action: 'The URL may be invalid or the content is unavailable. Try a different URL',
    retryable: false,
    severity: 'critical',
  },
  REDIRECT_LOOP: {
    title: 'Redirect Loop',
    reason: 'The website has a redirect loop that prevents content extraction',
    action: 'This URL cannot be analyzed. Try accessing the final destination URL directly',
    retryable: false,
    severity: 'critical',
  },
  NETWORK_ERROR: {
    title: 'Network Error',
    reason: 'Unable to connect to the website',
    action: 'Check your internet connection and try again',
    retryable: true,
    severity: 'critical',
  },
  EXTRACTION_FAILED: {
    title: 'Content Extraction Failed',
    reason: 'Unable to extract content from the URL',
    action: 'The page may not be accessible or may require authentication. Try a different URL',
    retryable: true,
    severity: 'critical',
  },
  EXTRACTION_ERROR: {
    title: 'Extraction Error',
    reason: 'An error occurred while extracting content',
    action: 'Try again or use a different URL',
    retryable: true,
    severity: 'critical',
  },
}
