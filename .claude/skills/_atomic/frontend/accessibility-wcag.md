---
name: accessibility-wcag
description: WCAG 2.1 - color contrast, keyboard, ARIA, screen readers
version: 1.0.0
tags: [accessibility, wcag, a11y, aria]
size: atomic
domain: frontend
---

# Accessibility (WCAG 2.1)

## Color Contrast

| Element | Minimum Ratio |
|---------|---------------|
| Normal text | 4.5:1 |
| Large text (18pt+) | 3:1 |
| UI components | 3:1 |

Test with: [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)

## Keyboard Navigation

```tsx
// All interactive elements must be keyboard accessible
<button
  onClick={handleClick}
  onKeyDown={(e) => e.key === 'Enter' && handleClick()}
>
  Click me
</button>

// Focus trap for modals
<Modal>
  <FocusTrap>
    {/* Modal content */}
  </FocusTrap>
</Modal>
```

## Skip Links

```tsx
<a href="#main-content" className="skip-link">
  Skip to main content
</a>

<main id="main-content" tabIndex={-1}>
  {/* Page content */}
</main>
```

## ARIA Attributes

```tsx
// Accessible button
<button
  aria-label="Close dialog"
  aria-expanded={isOpen}
  aria-controls="dialog-content"
>
  ×
</button>

// Live regions for dynamic content
<div aria-live="polite" aria-atomic="true">
  {statusMessage}
</div>

// Accessible form
<label htmlFor="email">Email</label>
<input
  id="email"
  aria-required="true"
  aria-invalid={hasError}
  aria-describedby="email-error"
/>
<span id="email-error">{errorMessage}</span>
```

## Semantic HTML

```tsx
// ✅ Use semantic elements
<nav>...</nav>
<main>...</main>
<article>...</article>
<button>...</button>

// ❌ Avoid div soup
<div onClick={...}>...</div>
<div role="navigation">...</div>
```

## Focus Management

```tsx
// Auto-focus dialog
const dialogRef = useRef<HTMLDivElement>(null)

useEffect(() => {
  if (isOpen) {
    dialogRef.current?.focus()
  }
}, [isOpen])

<div ref={dialogRef} tabIndex={-1} role="dialog">
  Dialog content
</div>
```

## Best Practices

- ✅ Use semantic HTML elements
- ✅ Provide text alternatives for images
- ✅ Ensure keyboard navigability
- ✅ Manage focus appropriately
- ✅ Test with screen readers
