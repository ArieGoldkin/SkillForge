import { startTransition, useOptimistic } from 'react'

import { Check, Copy } from 'lucide-react'

import { VALIDATION_CONSTANTS } from '@/lib/constants'
import { logger } from '@/lib/logger'

import { cn } from '@lib/utils'

import type { CopyButtonProps } from '../types'

/**
 * CopyButton - Copy text to clipboard with visual feedback
 *
 * Uses React 19's useOptimistic hook for instant UI feedback before
 * the async clipboard operation completes. Shows a copy icon by default,
 * transitions to a check icon with success styling after successful copy
 * for 2 seconds. Automatically rolls back on error.
 *
 * @example
 * ```tsx
 * <CopyButton text="const example = 'Hello World';" />
 * ```
 */
/* eslint-disable max-lines-per-function -- Component requires complete JSX with conditional styling and structured error logging */
export const CopyButton: React.FC<CopyButtonProps> = ({ text, className }) => {
  const [optimisticCopied, setOptimisticCopied] = useOptimistic(
    false,
    (_current, newValue: boolean) => newValue
  )

  const handleCopy = async () => {
    // Optimistic update - instant feedback
    setOptimisticCopied(true)

    startTransition(async () => {
      try {
        await navigator.clipboard.writeText(text)
        // Auto-reset after 2 seconds
        setTimeout(() => setOptimisticCopied(false), 2000)
      } catch (error) {
        // On error, the optimistic state rolls back automatically
        logger.error('Failed to copy text to clipboard', {
          textLength: text.length,
          textPreview:
            text.substring(0, VALIDATION_CONSTANTS.PREVIEW_TEXT_LENGTH) +
            (text.length > VALIDATION_CONSTANTS.PREVIEW_TEXT_LENGTH ? '...' : ''),
          error: error instanceof Error ? error.message : String(error),
          stack: error instanceof Error ? error.stack : undefined,
        })
        setOptimisticCopied(false)
      }
    })
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      data-testid="copy-button"
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1.5',
        'bg-(--code-border) border border-(--code-border)',
        'rounded-md font-sans text-xs font-medium',
        'text-zinc-400 cursor-pointer',
        'transition-all duration-200',
        'hover:bg-zinc-600 hover:text-white',
        'active:scale-95',
        optimisticCopied && [
          'bg-(--copy-success)',
          'text-white',
          'border-(--copy-success)',
          'animate-[copySuccess_0.3s_ease]',
        ],
        className
      )}
      aria-label={optimisticCopied ? 'Copied!' : 'Copy to clipboard'}
    >
      {optimisticCopied ? (
        <>
          <Check className="w-3.5 h-3.5" />
          <span>Copied!</span>
        </>
      ) : (
        <>
          <Copy className="w-3.5 h-3.5" />
          <span>Copy</span>
        </>
      )}
    </button>
  )
}

CopyButton.displayName = 'CopyButton'
