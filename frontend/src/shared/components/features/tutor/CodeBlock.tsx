import * as React from 'react'

import { Check, Copy } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Button } from '@/shared/components/ui/button'

/**
 * Props for CodeBlock component
 */
export interface CodeBlockProps {
  code: string
  language: string
  filename?: string
  showLineNumbers?: boolean
  className?: string
}

/**
 * CodeBlock - Syntax-highlighted code snippets in chat
 *
 * Displays code with syntax highlighting, copy functionality, and optional line numbers.
 * Theme adapts to light/dark mode. Supports horizontal scroll for long lines.
 *
 * Note: For production, integrate with a syntax highlighting library like
 * react-syntax-highlighter or Prism.js. This version uses basic styling.
 *
 * @example
 * ```tsx
 * <CodeBlock
 *   code={`const greeting = "Hello, world!";\nconsole.log(greeting);`}
 *   language="javascript"
 *   filename="example.js"
 *   showLineNumbers={true}
 * />
 * ```
 */
/* eslint-disable max-lines-per-function -- Component requires complete code block UI (header with filename/language/copy button, line numbers, pre/code elements with syntax highlighting). Copy functionality and line rendering logic necessitate current structure. */
export const CodeBlock: React.FC<CodeBlockProps> = ({
  code,
  language,
  filename,
  showLineNumbers = false,
  className,
}) => {
  const [isCopied, setIsCopied] = React.useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setIsCopied(true)
      setTimeout(() => setIsCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy code:', error)
    }
  }

  const lines = code.split('\n')

  return (
    <div
      className={cn(
        'group relative my-4 rounded-lg border border-primary/20 bg-muted overflow-hidden',
        className
      )}
    >
      {/* Header with filename and copy button */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/50">
        <div className="flex items-center gap-2">
          {filename && (
            <span className="text-xs font-medium text-muted-foreground">{filename}</span>
          )}
          {!filename && language && (
            <span className="text-xs font-medium text-muted-foreground uppercase">{language}</span>
          )}
        </div>

        {/* Copy button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className="h-7 px-2 opacity-0 group-hover:opacity-100 transition-opacity"
          aria-label={isCopied ? 'Copied!' : 'Copy code'}
        >
          {isCopied ? (
            <>
              <Check className="h-3 w-3 mr-1" />
              <span className="text-xs">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="h-3 w-3 mr-1" />
              <span className="text-xs">Copy</span>
            </>
          )}
        </Button>
      </div>

      {/* Code content */}
      <div className="overflow-x-auto">
        <pre className="p-4 text-sm">
          <code className={cn('block font-mono', `language-${language}`)}>
            {showLineNumbers ? (
              <table className="w-full border-collapse">
                <tbody>
                  {lines.map((line, index) => (
                    <tr key={index}>
                      <td className="pr-4 text-right text-muted-foreground select-none w-8">
                        {index + 1}
                      </td>
                      <td className="whitespace-pre">{line || '\n'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <span className="whitespace-pre">{code}</span>
            )}
          </code>
        </pre>
      </div>
    </div>
  )
}

CodeBlock.displayName = 'CodeBlock'
