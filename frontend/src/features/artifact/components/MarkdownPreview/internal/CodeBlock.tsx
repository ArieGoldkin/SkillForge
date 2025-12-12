import * as React from 'react'

import Prism from 'prismjs'
import 'prismjs/components/prism-typescript'
import 'prismjs/components/prism-javascript'
import 'prismjs/components/prism-python'
import 'prismjs/components/prism-bash'
import 'prismjs/components/prism-json'
import 'prismjs/components/prism-markdown'

import { cn } from '@lib/utils'

import type { CodeBlockComponentProps } from '../types'

import { CodeBlockHeader } from './CodeBlockHeader'

/**
 * CodeBlock - Syntax-highlighted code block with copy functionality
 *
 * Integrates Prism.js for syntax highlighting with support for multiple
 * languages. Includes a header with language label and copy button.
 *
 * @example
 * ```tsx
 * <CodeBlock
 *   code="const greeting = 'Hello, world!';"
 *   language="typescript"
 * />
 * ```
 */
export const CodeBlock: React.FC<CodeBlockComponentProps> = ({ code, language, className }) => {
  const codeRef = React.useRef<HTMLElement>(null)

  React.useEffect(() => {
    if (codeRef.current) {
      Prism.highlightElement(codeRef.current)
    }
  }, [])

  return (
    <div
      className={cn(
        'relative bg-(--code-bg) border border-(--code-border)',
        'rounded-lg my-6 overflow-hidden',
        'transition-shadow duration-200 hover:shadow-lg',
        className
      )}
      data-testid="code-block-container"
    >
      <CodeBlockHeader language={language} code={code} />

      <div className="overflow-x-auto">
        <pre className="m-0 p-4 bg-transparent">
          <code
            ref={codeRef}
            className={cn(
              `language-${language.toLowerCase()}`,
              'font-mono text-sm leading-relaxed',
              'text-(--code-text)'
            )}
            data-testid="code-block"
          >
            {code}
          </code>
        </pre>
      </div>
    </div>
  )
}

CodeBlock.displayName = 'CodeBlock'
