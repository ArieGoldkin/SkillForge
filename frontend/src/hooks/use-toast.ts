/**
 * Simple toast notification hook.
 * Uses native browser alert/confirm for now.
 * TODO: Replace with proper toast UI component (e.g., Sonner, React Hot Toast)
 */

import { logger } from '@/lib/logger'

export type ToastVariant = 'default' | 'destructive' | 'success'

export interface ToastOptions {
  title?: string
  description?: string
  variant?: ToastVariant
}

/**
 * Simple toast hook using console logging for development
 */
export function useToast() {
  const toast = (options: ToastOptions) => {
    const { title, description, variant = 'default' } = options
    const message = [title, description].filter(Boolean).join(': ')

    // Log to console for development (will be replaced with proper toast library)
    logger.info(`Toast notification`, { variant, message, title, description, service: 'toast' })

    // For production, you'd integrate a proper toast library here
  }

  return { toast }
}
