# TableOfContents Component

Sticky sidebar navigation for markdown content with automatic heading extraction and scroll tracking.

## Features

- **Automatic Extraction**: Extracts h2 and h3 headings from markdown content
- **Sticky Positioning**: Stays visible while scrolling on desktop
- **Active Section Highlighting**: Highlights the current section based on scroll position
- **Smooth Scrolling**: Smooth scroll animation when clicking a link
- **Responsive Design**: Collapsible on mobile (<1024px), sticky sidebar on desktop
- **Nested Structure**: h3 headings are nested under their parent h2
- **Accessibility**: Proper ARIA labels, keyboard navigation support

## Usage

```tsx
import { TableOfContents } from '@/features/artifact/components'

function ArtifactPage() {
  const content = `
## Introduction
This is the intro section.

### Getting Started
First steps here.

## Implementation
The main content.
  `

  return (
    <div className="lg:grid lg:grid-cols-[250px_1fr] lg:gap-8">
      <aside className="lg:sticky lg:top-8 lg:self-start">
        <TableOfContents content={content} />
      </aside>
      <main>
        <MarkdownPreview content={content} />
      </main>
    </div>
  )
}
```

## Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `content` | `string` | Yes | The markdown content to extract headings from |
| `className` | `string` | No | Additional CSS classes |

## Behavior

### Desktop (≥1024px)
- Displays as a sticky sidebar
- Always visible while scrolling
- Maximum height of `calc(100vh - 4rem)` with overflow scroll
- Custom scrollbar styling

### Mobile (<1024px)
- Collapsed by default
- Click "Table of Contents" to expand
- Shows above the main content
- Automatically collapses on window resize

### Active Section Tracking
- Tracks scroll position
- Highlights the heading closest to the top of the viewport
- 100px offset to account for sticky headers

## Styling

The component uses:
- Tailwind CSS utility classes for layout and spacing
- Custom CSS in `design-system/table-of-contents.css` for TOC-specific styles
- Design system variables from `src/index.css` for colors and theming

### Customization

You can customize the appearance by:
1. Passing additional classes via the `className` prop
2. Modifying `design-system/table-of-contents.css`
3. Overriding CSS variables in your theme

## Accessibility

- `<nav>` element with `aria-label="Table of contents"`
- `aria-expanded` attribute on the toggle button
- `aria-current="location"` on the active link
- Keyboard navigation support with visible focus indicators
- Reduced motion support for users with `prefers-reduced-motion`

## Implementation Details

### Heading ID Generation
- Headings in the markdown are automatically given IDs using the `slugify` function
- IDs are lowercase, hyphen-separated, with special characters removed
- Example: "Step 1: Getting Started" → `step-1-getting-started`

### Scroll Tracking
- Uses a custom `useActiveHeading` hook
- Listens to scroll events with passive listeners for performance
- Compares heading positions to scroll position + 100px offset

### Responsive Behavior
- Uses a custom `useTocCollapse` hook
- Automatically collapses on mobile, expands on desktop
- Listens to window resize events

## Testing

The component has comprehensive test coverage:

```bash
npm test -- src/features/artifact/components/TableOfContents
```

Tests include:
- Heading extraction from markdown
- Slug generation
- Component rendering
- Accessibility attributes
- Responsive behavior
- Edge cases (no headings, orphaned h3s, etc.)

## File Structure

```
TableOfContents/
├── TableOfContents.tsx       # Main component
├── types.ts                  # TypeScript types
├── utils.ts                  # Utility functions (slugify, extractHeadings)
├── index.ts                  # Public exports
├── hooks/
│   ├── useActiveHeading.ts   # Scroll tracking hook
│   └── useTocCollapse.ts     # Mobile collapse hook
└── __tests__/
    ├── TableOfContents.test.tsx
    └── utils.test.ts
```

## Related Components

- **MarkdownPreview**: Renders markdown content with custom heading renderers that add IDs
- **ArtifactPage**: Page component that uses TableOfContents in a two-column layout

## Performance Considerations

- Uses `useMemo` to avoid re-extracting headings on every render
- Passive event listeners for scroll tracking
- Debouncing not needed as scroll events are naturally throttled by the browser
- Small component size (~300 lines total including hooks and utils)
