import type { ElementType } from 'react'

import type { Components } from 'react-markdown'

import { cn } from '@lib/utils'

import { CodeBlock } from './CodeBlock'

type CodeComponent = NonNullable<Components['code']>
type CodeProps = CodeComponent extends ElementType<infer P> ? P : never

/**
 * Custom code renderer for ReactMarkdown
 * Renders code blocks with syntax highlighting, inline code as-is
 */
export const CodeRenderer: NonNullable<Components['code']> = (props) => {
  const {
    inline,
    className,
    children,
    node: _node,
    ...rest
  } = props as CodeProps & {
    inline?: boolean
  }
  const match = /language-(\w+)/.exec(className || '')
  const language = match ? match[1] : 'text'
  const codeContent = String(children).replace(/\n$/, '')

  if (inline) {
    return (
      <code className={className} {...rest}>
        {children}
      </code>
    )
  }

  return <CodeBlock code={codeContent} language={language} />
}

/**
 * Custom table renderer - wraps tables for responsive scrolling
 */
export const TableRenderer: NonNullable<Components['table']> = (props) => {
  const { children, node: _node, ...rest } = props
  return (
    <div className="table-wrapper">
      <table {...rest}>{children}</table>
    </div>
  )
}

/**
 * Custom input renderer - styles task list checkboxes
 */
export const InputRenderer: NonNullable<Components['input']> = (props) => {
  const { type, node: _node, ...rest } = props
  if (type === 'checkbox') {
    return <input type="checkbox" className="task-checkbox" {...rest} />
  }
  return <input type={type} {...rest} />
}

/**
 * Custom list item renderer - handles task list items
 */
export const ListItemRenderer: NonNullable<Components['li']> = (props) => {
  const { children, className, node: _node, ...rest } = props
  const isTaskItem = className?.includes('task-list-item')
  return (
    <li className={cn(isTaskItem && 'task-list-item', className)} {...rest}>
      {children}
    </li>
  )
}

/**
 * Custom unordered list renderer - handles task lists
 */
export const UnorderedListRenderer: NonNullable<Components['ul']> = (props) => {
  const { className, children, node: _node, ...rest } = props
  const isTaskList = className?.includes('contains-task-list')
  return (
    <ul className={cn(isTaskList && 'task-list', className)} {...rest}>
      {children}
    </ul>
  )
}
