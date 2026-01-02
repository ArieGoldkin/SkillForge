---
name: design-tokens
description: Design tokens - colors, typography, spacing, shadows
version: 1.0.0
tags: [design-system, tokens, css, theming]
size: atomic
domain: frontend
---

# Design Tokens

## Color Tokens

**Primitive** (raw values):
```json
{
  "color.primitive.blue.500": "#3b82f6",
  "color.primitive.blue.600": "#2563eb",
  "color.primitive.gray.900": "#111827"
}
```

**Semantic** (contextual meaning):
```json
{
  "color.brand.primary": "{color.primitive.blue.600}",
  "color.text.primary": "{color.primitive.gray.900}",
  "color.feedback.success": "{color.primitive.green.600}",
  "color.feedback.error": "{color.primitive.red.600}"
}
```

## Typography Tokens

```json
{
  "typography.fontSize.sm": "0.875rem",
  "typography.fontSize.base": "1rem",
  "typography.fontSize.lg": "1.125rem",
  "typography.fontWeight.medium": 500,
  "typography.fontWeight.bold": 700,
  "typography.lineHeight.normal": 1.5
}
```

## Spacing Tokens

```json
{
  "spacing.1": "0.25rem",
  "spacing.2": "0.5rem",
  "spacing.4": "1rem",
  "spacing.6": "1.5rem",
  "spacing.8": "2rem"
}
```

## Shadow Tokens

```json
{
  "shadow.sm": "0 1px 2px rgba(0,0,0,0.05)",
  "shadow.md": "0 4px 6px rgba(0,0,0,0.1)",
  "shadow.lg": "0 10px 15px rgba(0,0,0,0.1)"
}
```

## Border Radius

```json
{
  "borderRadius.sm": "0.125rem",
  "borderRadius.md": "0.375rem",
  "borderRadius.lg": "0.5rem",
  "borderRadius.full": "9999px"
}
```

## CSS Variables

```css
:root {
  --color-brand-primary: #2563eb;
  --color-text-primary: #111827;
  --spacing-4: 1rem;
  --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
}

[data-theme="dark"] {
  --color-brand-primary: #3b82f6;
  --color-text-primary: #f9fafb;
}
```

## Accessibility

- Normal text: 4.5:1 contrast minimum
- Large text (18pt+): 3:1 minimum
- UI components: 3:1 minimum
