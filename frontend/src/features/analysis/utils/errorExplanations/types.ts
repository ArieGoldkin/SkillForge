/**
 * Error explanation type definition
 */
export interface ErrorExplanation {
  title: string
  reason: string
  action: string
  retryable: boolean
  severity: 'critical' | 'non-critical'
}
