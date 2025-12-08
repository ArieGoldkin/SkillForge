import React from 'react'

import type { Components } from 'react-markdown'

import { cn } from '@lib/utils'

const extractTextFromReact = (nodes: React.ReactNode): string => {
  return React.Children.toArray(nodes)
    .map((child: React.ReactNode) => {
      if (typeof child === 'string' || typeof child === 'number') {
        return String(child)
      }
      if (React.isValidElement(child)) {
        const element = child as React.ReactElement<{ children?: React.ReactNode }>
        if (element.props?.children) {
          return extractTextFromReact(element.props.children)
        }
      }
      return ''
    })
    .join('')
    .trim()
}

const extractTextFromMdast = (mdastNode: unknown): string => {
  if (!mdastNode || typeof mdastNode !== 'object') return ''
  if ('value' in (mdastNode as Record<string, unknown>)) {
    const value = (mdastNode as { value?: unknown }).value
    if (typeof value === 'string') return value
  }
  if ('children' in (mdastNode as Record<string, unknown>)) {
    const children = (mdastNode as { children?: unknown }).children
    if (Array.isArray(children)) {
      return children.map((child: unknown) => extractTextFromMdast(child)).join('')
    }
  }
  return ''
}

/**
 * Custom paragraph renderer that formats metadata lines (Source/Generated/Analysis ID)
 * onto separate lines for readability.
 *
 * Falls back to a normal paragraph when the expected metadata markers are absent.
 */
export const ParagraphRenderer: NonNullable<Components['p']> = (props) => {
  const { children, node, ...rest } = props

  const textFromNode = extractTextFromMdast(node)
  const text = textFromNode || extractTextFromReact(children) || String(children ?? '')

  const sourceMatch = text.match(/Source:\s*([^\s]+)\s*/)
  const generatedMatch = text.match(/Generated:\s*([^\n]+?)\s*(Analysis ID:|$)/)
  const analysisMatch = text.match(/Analysis ID:\s*([^\s]+)/)

  const sourceUrl = sourceMatch?.[1]
  const generatedText = generatedMatch?.[1]?.trim()
  const analysisId = analysisMatch?.[1]

  const hasMetadataLayout = Boolean(
    sourceUrl || generatedText || analysisId || text.includes('Source:')
  )

  if (!hasMetadataLayout) {
    return (
      <p {...rest} className={cn(rest.className)}>
        {children}
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-1 text-sm leading-relaxed">
      {sourceUrl && (
        <div>
          <span className="font-semibold">Source:</span>{' '}
          <a
            href={sourceUrl}
            target="_blank"
            rel="noreferrer"
            className="underline text-primary hover:text-primary/80"
          >
            {sourceUrl}
          </a>
        </div>
      )}
      {generatedText && (
        <div>
          <span className="font-semibold">Generated:</span> {generatedText}
        </div>
      )}
      {analysisId && (
        <div>
          <span className="font-semibold">Analysis ID:</span> {analysisId}
        </div>
      )}
    </div>
  )
}
