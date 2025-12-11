import * as React from 'react'

import { Check, Copy } from 'lucide-react'

import { cn } from '@lib/utils'

import type { CopyButtonProps } from '../types'

/**
 * CopyButton - Copy text to clipboard with visual feedback
 *
 * Shows a copy icon by default, transitions to a check icon with success
 * styling after successful copy for 2 seconds.
 *
 * @example
 * ```tsx
 * <CopyButton text="const example = 'Hello World';" />
 * ```
 */
export const CopyButton: React.FC<CopyButtonProps> = ({ text, className }) => {
  const [isCopied, setIsCopied] = React.useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setIsCopied(true)
      setTimeout(() => setIsCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy to clipboard:', error)
    }
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
        isCopied && [
          'bg-(--copy-success)',
          'text-white',
          'border-(--copy-success)',
          'animate-[copySuccess_0.3s_ease]',
        ],
        className
      )}
      aria-label={isCopied ? 'Copied!' : 'Copy to clipboard'}
    >
      {isCopied ? (
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
