---
name: theming-dark-mode
description: Theming with CSS variables and dark mode
version: 1.0.0
tags: [theming, dark-mode, css, tailwind]
size: atomic
domain: frontend
---

# Theming & Dark Mode

## CSS Variables Approach

```css
:root {
  --color-bg-primary: #ffffff;
  --color-bg-secondary: #f9fafb;
  --color-text-primary: #111827;
  --color-text-secondary: #6b7280;
  --color-brand-primary: #2563eb;
}

[data-theme="dark"] {
  --color-bg-primary: #111827;
  --color-bg-secondary: #1f2937;
  --color-text-primary: #f9fafb;
  --color-text-secondary: #9ca3af;
  --color-brand-primary: #3b82f6;
}
```

```tsx
// Toggle theme
document.documentElement.setAttribute('data-theme', 'dark')
```

## Tailwind CSS Dark Mode

```tsx
<div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
  Content
</div>
```

```js
// tailwind.config.js
module.exports = {
  darkMode: 'class',  // or 'media' for system preference
}
```

## ThemeProvider Pattern

```typescript
const lightTheme = {
  colors: { background: '#fff', text: '#000' }
}

const darkTheme = {
  colors: { background: '#000', text: '#fff' }
}

function App() {
  const [isDark, setIsDark] = useState(false)

  return (
    <ThemeProvider theme={isDark ? darkTheme : lightTheme}>
      <button onClick={() => setIsDark(!isDark)}>Toggle</button>
      <Content />
    </ThemeProvider>
  )
}
```

## System Preference Detection

```typescript
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)')

prefersDark.addEventListener('change', (e) => {
  setIsDark(e.matches)
})
```

## Persist Preference

```typescript
// Save
localStorage.setItem('theme', isDark ? 'dark' : 'light')

// Load
const saved = localStorage.getItem('theme')
const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches
const initialDark = saved ? saved === 'dark' : systemDark
```

## Best Practices

- ✅ Respect system preference by default
- ✅ Persist user choice
- ✅ Use CSS variables for flexibility
- ✅ Test contrast in both modes
