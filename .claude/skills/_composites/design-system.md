---
name: design-system
description: Complete design system with tokens, atomic design, theming
version: 1.0.0
tags: [design-system, tokens, components, accessibility]
size: composite
atomics:
  - frontend/design-tokens
  - frontend/atomic-design
  - frontend/component-api
  - frontend/theming-dark-mode
  - frontend/accessibility-wcag
---

# Design System Composite

Complete design system knowledge for scalable UI.

## When to Use

- Creating design systems from scratch
- Establishing design token standards
- Building component libraries
- Implementing dark mode
- Ensuring WCAG compliance

## Atomic Skills

### 1. Design Tokens (`design-tokens`)
Colors, typography, spacing, shadows as variables.

### 2. Atomic Design (`atomic-design`)
Atoms → Molecules → Organisms → Templates → Pages.

### 3. Component API (`component-api`)
Props patterns, polymorphic components, composition.

### 4. Theming (`theming-dark-mode`)
CSS variables, Tailwind dark mode, ThemeProvider.

### 5. Accessibility (`accessibility-wcag`)
Color contrast, keyboard nav, ARIA, screen readers.

## Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│  DESIGN SYSTEM CHECKLIST                                    │
├─────────────────────────────────────────────────────────────┤
│  □ Define design tokens (colors, spacing, typography)       │
│  □ Create primitive components (atoms)                      │
│  □ Compose molecules and organisms                          │
│  □ Implement light/dark theming                             │
│  □ Ensure 4.5:1 contrast ratio                              │
│  □ Test keyboard navigation                                 │
│  □ Add ARIA attributes                                      │
└─────────────────────────────────────────────────────────────┘
```

## Load Order

1. `design-tokens` - Foundation variables
2. `atomic-design` - Component hierarchy
3. `component-api` - API patterns
4. `theming-dark-mode` - Theme implementation
5. `accessibility-wcag` - A11y compliance
