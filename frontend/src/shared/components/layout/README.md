# Layout Components

## Components

### ThemeToggle

Interactive theme switcher with three states: light, dark, and system.

**Features:**
- Three-state cycle: Light → Dark → System → Light
- Icons: Sun (light), Moon (dark), Monitor (system)
- Tooltip showing current mode
- localStorage persistence
- System preference detection
- Accessible with ARIA labels

**Usage:**
```tsx
import { ThemeToggle } from '@/shared/components/layout';

<ThemeToggle />
```

### AppShell

Main application layout wrapper providing sticky navigation, optional sidebar, and content area.

**Features:**
- Sticky navigation header
- Optional collapsible sidebar
- Responsive design (sidebar collapses on mobile)
- Smooth transitions
- Semantic HTML structure
- Proper ARIA labels

**Props:**
- `children: ReactNode` - Main page content
- `sidebar?: ReactNode` - Optional sidebar content
- `showSidebar?: boolean` - Whether to show the sidebar (default: false)

**Usage:**
```tsx
import { AppShell } from '@/shared/components/layout';

// Simple layout without sidebar
<AppShell>
  <PageContent />
</AppShell>

// Layout with sidebar
<AppShell
  sidebar={<FilterPanel />}
  showSidebar
>
  <PageContent />
</AppShell>
```

## Theme System

The theme system uses Zustand for state management and supports:

1. **Three theme modes:**
   - `light` - Light theme
   - `dark` - Dark theme
   - `system` - Follows OS preference

2. **Storage:**
   - Key: `skillforge-theme`
   - Persists across sessions

3. **Application:**
   - Sets `data-theme` attribute on `<html>`
   - Also sets CSS class for compatibility
   - Listens for OS theme changes when in system mode

4. **Implementation:**
```tsx
import { useThemeStore, applyTheme } from '@/stores/themeStore';

// Get current theme
const theme = useThemeStore(state => state.theme);

// Set theme
const setTheme = useThemeStore(state => state.setTheme);
setTheme('dark');

// Toggle through themes
const toggleTheme = useThemeStore(state => state.toggleTheme);
toggleTheme(); // light → dark → system → light
```

## Component Customizations

### Button
- Added `teal` variant for prominent teal-colored buttons
- Enhanced focus ring (2px width with offset)

### Badge
- Added status variants:
  - `success` - Green (completed)
  - `warning` - Yellow (in-progress)
  - `error` - Red (failed)
  - `info` - Blue (pending)

### Input
- Added `error` prop for validation state
- Enhanced focus ring (2px width with offset)
- Red border when error is true

## Accessibility

All layout components follow WCAG 2.1 AA guidelines:

- Semantic HTML (`<nav>`, `<main>`, `<aside>`)
- Proper ARIA labels and roles
- Keyboard navigation support
- Focus visible states with ring indicators
- Tooltips for icon-only buttons
- Color contrast ratios meet standards

## Responsive Design

- **Mobile (<768px):**
  - Navigation links collapse
  - Sidebar hidden by default
  - Floating toggle button for sidebar

- **Tablet (768px - 1024px):**
  - Navigation links visible
  - Sidebar sticky and always visible (if enabled)

- **Desktop (>1024px):**
  - Full layout with all features
  - Larger spacing and typography
