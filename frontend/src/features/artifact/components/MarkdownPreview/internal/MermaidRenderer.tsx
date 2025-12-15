import { useEffect, useRef } from 'react'

import mermaid from 'mermaid'

import { cn } from '@lib/utils'

interface MermaidRendererProps {
  code: string
  className?: string
}

// Module-level flag for global initialization (shared across all instances)
let isMermaidInitialized = false

/**
 * Initialize mermaid with default configuration (only once globally)
 */
const initializeMermaid = () => {
  if (isMermaidInitialized) return

  mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    fontFamily: 'inherit',
    fontSize: 14,
    // Flowchart configuration for proper text rendering (Issue #299-304)
    flowchart: {
      htmlLabels: true, // Enable HTML labels for better text handling
      nodeSpacing: 50, // Space between nodes
      rankSpacing: 50, // Space between ranks
      curve: 'basis', // Smooth curves
      padding: 15, // Padding inside nodes
      useMaxWidth: false, // Don't constrain to container width
    },
    // Ensure proper wrapping for long text
    themeVariables: {
      fontSize: '14px',
      fontFamily: 'inherit',
    },
  })
  isMermaidInitialized = true
}

/**
 * Inject custom CSS styles for proper text rendering (Issue #299-304)
 * Only adds styles once globally
 */
const injectCustomStyles = () => {
  if (document.getElementById('mermaid-custom-styles')) return

  const styleEl = document.createElement('style')
  styleEl.id = 'mermaid-custom-styles'
  styleEl.textContent = `
    .mermaid-container svg {
      max-width: 100%;
      height: auto;
      white-space: normal;
    }
    .mermaid-container .node rect {
      rx: 5;
      ry: 5;
      min-width: 150px !important;
    }
    .mermaid-container .nodeLabel,
    .mermaid-container .node .label {
      white-space: normal !important;
      overflow: visible !important;
      word-break: break-word;
    }
    .mermaid-container text {
      overflow: visible !important;
      font-size: 13px !important;
    }
    .mermaid-container .node rect,
    .mermaid-container .node polygon,
    .mermaid-container .node circle,
    .mermaid-container .node ellipse {
      fill: #f9fafb;
      stroke: #e5e7eb;
    }
  `
  document.head.appendChild(styleEl)
}

/**
 * Render a mermaid diagram and insert it into the DOM element
 * Includes bindFunctions call for interactive diagrams
 */
const renderMermaidDiagram = async (element: HTMLDivElement, code: string) => {
  if (!element || !code.trim()) return

  try {
    const id = `mermaid-${Math.random().toString(36).substring(2, 11)}`
    element.innerHTML = ''
    const { svg, bindFunctions } = await mermaid.render(id, code)
    if (element) {
      element.innerHTML = svg
      // Call bindFunctions for interactive diagrams (click handlers, etc.)
      bindFunctions?.(element)
    }
  } catch (error) {
    console.error('Mermaid rendering error:', error)
    if (element) {
      // Escape code to prevent XSS
      const escapedCode = code
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
      element.innerHTML = `
        <div class="mermaid-error">
          <p class="text-sm text-destructive mb-2">Failed to render diagram</p>
          <pre class="text-xs"><code>${escapedCode}</code></pre>
        </div>
      `
    }
  }
}

/**
 * MermaidRenderer - Renders Mermaid diagrams from code blocks
 *
 * Features:
 * - Global single initialization of mermaid.js (shared across instances)
 * - Re-renders on code changes
 * - Supports interactive diagrams via bindFunctions
 * - Error handling with fallback to code display
 * - Custom CSS for proper text rendering (Issue #299-304)
 */
export const MermaidRenderer: React.FC<MermaidRendererProps> = ({ code, className }) => {
  const elementRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Initialize mermaid globally (idempotent - only runs once)
    initializeMermaid()
    // Add custom styles for proper text rendering (Issue #299-304)
    injectCustomStyles()
  }, [])

  useEffect(() => {
    if (elementRef.current) {
      renderMermaidDiagram(elementRef.current, code)
    }
  }, [code])

  return (
    <div
      ref={elementRef}
      className={cn(
        'mermaid-container',
        'my-4 p-4',
        'bg-muted/30 rounded-lg',
        'border border-border',
        'overflow-x-auto',
        className
      )}
      data-testid="mermaid-diagram"
    />
  )
}

MermaidRenderer.displayName = 'MermaidRenderer'
