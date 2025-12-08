import type React from 'react'
import type { ElementType } from 'react'

import type { Components } from 'react-markdown'

import { cn } from '@lib/utils'

import { CodeBlock } from './CodeBlock'
import { ParagraphRenderer } from './ParagraphRenderer'

type CodeComponent = NonNullable<Components['code']>
type CodeProps = CodeComponent extends ElementType<infer P> ? P : never
type CodeRendererProps = CodeProps &
  React.ComponentProps<'code'> & {
    inline?: boolean
    className?: string
    children?: React.ReactNode
    node?: unknown
  }

/**
 * Custom code renderer for ReactMarkdown
 * Renders code blocks with syntax highlighting, inline code as simple styled spans
 *
 * Detection logic for react-markdown v9+:
 * - Code blocks have className with "language-" prefix (from ```lang blocks)
 * - Inline code has no language class and typically no newlines
 * - The deprecated `inline` prop is checked as fallback for compatibility
 */
export const CodeRenderer = ((rawProps: CodeRendererProps) => {
  const { inline, className, children, node: _node, ...rest } = rawProps
  const match = /language-(\w+)/.exec(className || '')
  const language = match ? match[1] : 'text'
  const codeContent = String(children).replace(/\n$/, '')

  // Detect inline code: either explicit inline prop, or no language class and no newlines
  // This handles react-markdown v9+ which deprecated the inline prop
  const hasLanguageClass = Boolean(match)
  const hasNewlines = codeContent.includes('\n')
  const isInlineCode = inline === true || (!hasLanguageClass && !hasNewlines)

  if (isInlineCode) {
    return (
      <code
        className={cn(
          'inline-code',
          'px-1.5 py-0.5 mx-0.5',
          'bg-muted/50 text-foreground',
          'rounded font-mono text-[0.9em]',
          'border border-border/50',
          className
        )}
        {...rest}
      >
        {children}
      </code>
    )
  }

  return <CodeBlock code={codeContent} language={language} />
}) satisfies NonNullable<Components['code']>

/**
 * Custom table renderer - wraps tables for responsive scrolling
 */
type TableRendererProps = React.ComponentProps<'table'> & {
  children?: React.ReactNode
  node?: unknown
}

export const TableRenderer = ((rawProps: TableRendererProps) => {
  const { children, node: _node, ...rest } = rawProps
  return (
    <div className="table-wrapper">
      <table {...rest}>{children}</table>
    </div>
  )
}) satisfies NonNullable<Components['table']>

/**
 * Custom input renderer - styles task list checkboxes
 */
type InputRendererProps = React.ComponentProps<'input'> & {
  type?: string
  node?: unknown
}

export const InputRenderer = ((rawProps: InputRendererProps) => {
  const { type, node: _node, ...rest } = rawProps
  if (type === 'checkbox') {
    return <input type="checkbox" className="task-checkbox" {...rest} />
  }
  return <input type={type} {...rest} />
}) satisfies NonNullable<Components['input']>

/**
 * Custom list item renderer - handles task list items
 */
type ListItemRendererProps = React.ComponentProps<'li'> & {
  className?: string
  children?: React.ReactNode
  node?: unknown
}

export const ListItemRenderer = ((rawProps: ListItemRendererProps) => {
  const { children, className, node: _node, ...rest } = rawProps
  const isTaskItem = className?.includes('task-list-item')
  return (
    <li className={cn(isTaskItem && 'task-list-item', className)} {...rest}>
      {children}
    </li>
  )
}) satisfies NonNullable<Components['li']>

/**
 * Custom unordered list renderer - handles task lists
 */
type UnorderedListRendererProps = React.ComponentProps<'ul'> & {
  className?: string
  children?: React.ReactNode
  node?: unknown
}

export const UnorderedListRenderer = ((rawProps: UnorderedListRendererProps) => {
  const { className, children, node: _node, ...rest } = rawProps
  const isTaskList = className?.includes('contains-task-list')
  return (
    <ul className={cn(isTaskList && 'task-list', className)} {...rest}>
      {children}
    </ul>
  )
}) satisfies NonNullable<Components['ul']>

// Re-export paragraph renderer
export { ParagraphRenderer }
