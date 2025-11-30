import type * as React from 'react'

import { cn } from '@lib/utils'

import { LANGUAGE_COLORS } from '../constants'

import { CopyButton } from './CopyButton'

interface CodeBlockHeaderProps {
  language: string
  code: string
}

/**
 * CodeBlockHeader - Header section with language label and copy button
 */
export const CodeBlockHeader: React.FC<CodeBlockHeaderProps> = ({ language, code }) => {
  const languageColor = LANGUAGE_COLORS[language.toLowerCase()] || LANGUAGE_COLORS.default

  return (
    <div
      className={cn(
        'flex items-center justify-between',
        'px-4 py-2',
        'bg-(--code-header-bg)',
        'border-b border-(--code-border)'
      )}
    >
      <div className="flex items-center gap-2">
        <span
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: languageColor }}
          aria-hidden="true"
        />
        <span className="font-mono text-xs text-muted-foreground lowercase">{language}</span>
      </div>

      <CopyButton text={code} />
    </div>
  )
}

CodeBlockHeader.displayName = 'CodeBlockHeader'
