import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

import { MarkdownPreview } from '../index'

// Mock mermaid library
vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn().mockResolvedValue({
      svg: '<svg data-testid="mermaid-svg" class="mermaid-diagram">Rendered Diagram</svg>',
    }),
  },
}))

describe('MarkdownPreview - Mermaid Integration', () => {
  it('should render mermaid code blocks as diagrams', async () => {
    const markdownWithMermaid = `
# Test Document

Here's a mermaid diagram:

\`\`\`mermaid
graph TD;
  A-->B;
  B-->C;
  C-->D;
\`\`\`

And some more text.
    `

    render(<MarkdownPreview content={markdownWithMermaid} showMetadata={false} />)

    // Check that the mermaid container is rendered
    await waitFor(() => {
      const container = screen.getByTestId('mermaid-diagram')
      expect(container).toBeInTheDocument()
      expect(container).toHaveClass('mermaid-container')
    })
  })

  it('should render regular code blocks normally', () => {
    const markdownWithCode = `
# Test Document

\`\`\`javascript
const x = 42;
console.log(x);
\`\`\`
    `

    render(<MarkdownPreview content={markdownWithCode} showMetadata={false} />)

    // Regular code should not have mermaid container
    expect(screen.queryByTestId('mermaid-diagram')).not.toBeInTheDocument()
  })

  it('should handle multiple mermaid diagrams', async () => {
    const markdownWithMultipleMermaid = `
# Test Document

\`\`\`mermaid
graph TD;
  A-->B;
\`\`\`

Some text between diagrams.

\`\`\`mermaid
sequenceDiagram
  Alice->>Bob: Hello
\`\`\`
    `

    render(<MarkdownPreview content={markdownWithMultipleMermaid} showMetadata={false} />)

    // Check that both mermaid containers are rendered
    await waitFor(() => {
      const containers = screen.getAllByTestId('mermaid-diagram')
      expect(containers).toHaveLength(2)
    })
  })

  it('should handle mixed content with mermaid and code blocks', async () => {
    const mixedContent = `
# Architecture

\`\`\`mermaid
graph LR;
  Frontend-->Backend;
\`\`\`

## Implementation

\`\`\`typescript
const app = express();
\`\`\`
    `

    render(<MarkdownPreview content={mixedContent} showMetadata={false} />)

    // Should have one mermaid diagram
    await waitFor(() => {
      const mermaidContainers = screen.getAllByTestId('mermaid-diagram')
      expect(mermaidContainers).toHaveLength(1)
    })

    // Regular code blocks should not be mermaid
    expect(screen.queryAllByTestId('mermaid-diagram')).toHaveLength(1)
  })
})
