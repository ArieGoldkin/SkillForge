# SkillForge Design System

**Version 1.0** - Clean Modern Design with Teal Accents

## Overview

The SkillForge design system is built on top of shadcn/ui with custom OKLCH colors, Outfit typography, and Tailwind CSS v4.

### Key Features

- **OKLCH Color Space**: Perceptually uniform colors for consistent visual experience
- **Teal Accent**: Primary brand color with proper contrast ratios
- **Outfit Font**: Modern, clean Google Font with variable weights
- **shadcn/ui Components**: Pre-built, accessible React components
- **Tailwind CSS v4**: Utility-first CSS framework with custom design tokens

## File Structure

```
src/design-system/
├── README.md         # This file
├── tokens.ts         # TypeScript design tokens (colors, typography, spacing, etc.)
├── theme.css         # CSS variables for light/dark themes
└── index.ts          # Central export point
```

## Usage

### Using Design Tokens in TypeScript

```typescript
import { lightColors, darkColors, fonts, spacing, shadows } from '@/design-system';

// Access color values
const primaryColor = lightColors.primary; // 'oklch(0.8348 0.1302 160.9080)'

// Access typography
const headingFont = fonts.sans; // 'Outfit, sans-serif'

// Access spacing
const padding = spacing[4]; // '1rem'
```

### Using CSS Variables in Components

All tokens are available as CSS variables in both light and dark themes:

```tsx
// In Tailwind classes
<div className="bg-primary text-primary-foreground">Teal Button</div>
<div className="font-sans text-base">Outfit Font</div>
<div className="shadow-lg rounded-lg">Card with Shadow</div>

// In custom CSS
.custom-component {
  background-color: var(--primary);
  color: var(--primary-foreground);
  font-family: var(--font-sans);
  border-radius: var(--radius);
  box-shadow: var(--shadow-md);
}
```

### Using shadcn/ui Components

Import components from `@/components/ui`:

```tsx
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

function MyComponent() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Welcome to SkillForge</CardTitle>
      </CardHeader>
      <CardContent>
        <Input placeholder="Enter your email" />
        <Button className="mt-4">Get Started</Button>
        <Badge>New</Badge>
      </CardContent>
    </Card>
  );
}
```

## Color Palette

### Light Theme

- **Primary (Teal)**: `oklch(0.8348 0.1302 160.9080)` - Main brand color
- **Background**: `oklch(0.9911 0 0)` - Near white
- **Foreground**: `oklch(0.2046 0 0)` - Dark text
- **Muted**: `oklch(0.9461 0 0)` - Subtle backgrounds
- **Destructive**: `oklch(0.5523 0.1927 32.7272)` - Error/danger

### Dark Theme

- **Primary (Teal)**: `oklch(0.4365 0.1044 156.7556)` - Darker teal for contrast
- **Background**: `oklch(0.1822 0 0)` - Near black
- **Foreground**: `oklch(0.9288 0.0126 255.5078)` - Light text
- **Ring (Focus)**: `oklch(0.8003 0.1821 151.7110)` - Bright teal for focus states

## Typography

### Font Families

- **Sans**: `Outfit, sans-serif` (Primary)
- **Serif**: `ui-serif, Georgia, Cambria, Times New Roman, Times, serif`
- **Mono**: `monospace`

### Font Sizes

- **h1**: `3rem` (48px)
- **h2**: `2rem` (32px)
- **h3**: `1.5rem` (24px)
- **base**: `1rem` (16px)
- **sm**: `0.875rem` (14px)
- **xs**: `0.75rem` (12px)

### Font Weights

- **Normal**: 400
- **Medium**: 500
- **Semibold**: 600
- **Bold**: 700

## Spacing Scale

Base unit: `0.25rem` (4px)

```
0: 0
1: 0.25rem (4px)
2: 0.5rem (8px)
3: 0.75rem (12px)
4: 1rem (16px)
5: 1.25rem (20px)
6: 1.5rem (24px)
8: 2rem (32px)
10: 2.5rem (40px)
12: 3rem (48px)
16: 4rem (64px)
20: 5rem (80px)
24: 6rem (96px)
```

## Border Radius

- **sm**: `calc(0.5rem - 4px)` (4px)
- **md**: `calc(0.5rem - 2px)` (6px)
- **lg**: `0.5rem` (8px) - Default
- **xl**: `calc(0.5rem + 4px)` (12px)
- **full**: `9999px`

## Shadows

All shadows use subtle opacity for depth perception:

- **2xs/xs**: `0px 1px 3px 0px hsl(0 0% 0% / 0.09)` - Minimal
- **sm**: `0px 1px 3px 0px hsl(0 0% 0% / 0.17), 0px 1px 2px -1px hsl(0 0% 0% / 0.17)` - Small
- **md**: `0px 1px 3px 0px hsl(0 0% 0% / 0.17), 0px 2px 4px -1px hsl(0 0% 0% / 0.17)` - Medium
- **lg**: `0px 1px 3px 0px hsl(0 0% 0% / 0.17), 0px 4px 6px -1px hsl(0 0% 0% / 0.17)` - Large
- **xl**: `0px 1px 3px 0px hsl(0 0% 0% / 0.17), 0px 8px 10px -1px hsl(0 0% 0% / 0.17)` - Extra large
- **2xl**: `0px 1px 3px 0px hsl(0 0% 0% / 0.43)` - Maximum

## Theme Switching

The design system supports automatic theme switching based on system preferences and manual theme selection:

```tsx
// Set theme manually
document.documentElement.setAttribute('data-theme', 'dark');
document.documentElement.setAttribute('data-theme', 'light');

// Or use class-based approach (for Tailwind dark mode)
document.documentElement.classList.add('dark');
document.documentElement.classList.remove('dark');
```

## Installed shadcn/ui Components

- **Button** - Primary, secondary, destructive, outline, ghost, and link variants
- **Card** - Container with header, content, and footer sections
- **Input** - Text input with proper focus states
- **Dialog** - Modal dialog with overlay
- **Tabs** - Tabbed interface for content organization
- **Badge** - Small status indicators
- **Progress** - Progress bar component
- **Tooltip** - Hover tooltips for additional information

## Adding New Components

To add more shadcn/ui components:

```bash
npx shadcn@latest add [component-name]
```

Example:
```bash
npx shadcn@latest add dropdown-menu
npx shadcn@latest add select
npx shadcn@latest add calendar
```

## Best Practices

1. **Use CSS Variables**: Always use CSS variables (`var(--primary)`) instead of hardcoded values
2. **Semantic Colors**: Use semantic color names (primary, destructive, muted) instead of generic names
3. **OKLCH Over RGB**: Prefer OKLCH for new colors to maintain perceptual uniformity
4. **Responsive Design**: Use Tailwind's responsive prefixes (`sm:`, `md:`, `lg:`)
5. **Accessibility**: Ensure WCAG 2.1 AA compliance (4.5:1 contrast for normal text, 3:1 for large text)
6. **Type Safety**: Import types from `@/design-system` for better TypeScript support

## Next Steps (Phase 2)

- Create custom component variants with SkillForge branding
- Build composite components (e.g., FeatureCard, LearningPathCard)
- Add animation utilities and transitions
- Create Storybook stories for component documentation
- Implement theme switcher component
