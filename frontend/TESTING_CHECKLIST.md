# Issue #32 Testing Checklist

## Automated Tests ✅

- [x] TypeScript compilation: `npm run build` - PASS
- [x] ESLint checks: `npm run lint` - PASS (0 errors, 0 warnings)
- [x] Biome formatting: `npm run format:check` - PASS
- [x] Full quality suite: `npm run quality:check` - PASS
- [x] Production build: Successful, bundle size ~122KB gzipped

## Manual Testing Checklist

### Theme Toggle Testing

- [ ] **Initial Load**
  - [ ] Open app in browser
  - [ ] Verify theme loads from localStorage (or defaults to system)
  - [ ] Check that CSS variables are applied correctly

- [ ] **Theme Cycling**
  - [ ] Click theme toggle button
  - [ ] Verify cycle: Light → Dark → System → Light
  - [ ] Check icon changes: Sun (light) → Moon (dark) → Monitor (system)
  - [ ] Verify tooltip text updates correctly

- [ ] **Persistence**
  - [ ] Toggle to dark mode
  - [ ] Reload page
  - [ ] Verify dark mode persists
  - [ ] Check localStorage key `skillforge-theme` has correct value

- [ ] **System Theme Detection**
  - [ ] Set theme toggle to "System"
  - [ ] Change OS theme preference (light/dark)
  - [ ] Verify app theme updates automatically
  - [ ] Check that data-theme attribute updates on `<html>`

- [ ] **Visual Verification**
  - [ ] Open DevTools
  - [ ] Check `<html>` element has `data-theme="light"` or `"dark"` attribute
  - [ ] Check `<html>` element has `.light` or `.dark` class
  - [ ] Verify CSS variables switch in Computed styles

### Navigation Component Testing

- [ ] **Desktop View (>1024px)**
  - [ ] Verify navigation is sticky at top
  - [ ] Check backdrop blur effect works
  - [ ] Verify all navigation links visible
  - [ ] Test link hover states
  - [ ] Test active link highlighting

- [ ] **Tablet View (768px - 1024px)**
  - [ ] Verify navigation links still visible
  - [ ] Check responsive padding works
  - [ ] Test navigation actions (theme toggle, user button)

- [ ] **Mobile View (<768px)**
  - [ ] Verify SkillForge logo visible
  - [ ] Check navigation links collapse appropriately
  - [ ] Test theme toggle button works
  - [ ] Test user menu button

- [ ] **Accessibility**
  - [ ] Use Tab key to navigate through all interactive elements
  - [ ] Verify focus rings visible on all buttons/links
  - [ ] Press Enter on focused elements to activate
  - [ ] Check aria-labels with screen reader (if available)

### Button Component Testing

- [ ] **Variants**
  - [ ] Default button renders correctly
  - [ ] Teal variant displays teal color
  - [ ] Secondary, destructive, outline, ghost, link variants work
  - [ ] Hover states transition smoothly

- [ ] **Sizes**
  - [ ] Small, default, large buttons render at correct sizes
  - [ ] Icon button (square) renders correctly

- [ ] **States**
  - [ ] Disabled state shows reduced opacity
  - [ ] Disabled buttons not clickable
  - [ ] Focus ring appears on keyboard focus

- [ ] **Accessibility**
  - [ ] Tab to buttons
  - [ ] Press Enter/Space to activate
  - [ ] Verify focus ring uses teal color (ring-2 ring-ring)

### Badge Component Testing

- [ ] **Standard Variants**
  - [ ] Default badge (teal background)
  - [ ] Secondary badge (gray background)
  - [ ] Destructive badge (red background)
  - [ ] Outline badge (border only)

- [ ] **Status Variants**
  - [ ] Success badge (green) - readable text
  - [ ] Warning badge (yellow) - readable text
  - [ ] Error badge (red) - readable text
  - [ ] Info badge (blue) - readable text

- [ ] **Visual Check**
  - [ ] Badges have proper padding
  - [ ] Text is legible in both light and dark themes
  - [ ] Colors match SkillForge design tokens

### Input Component Testing

- [ ] **Normal State**
  - [ ] Input renders with border
  - [ ] Placeholder text visible
  - [ ] Typing updates value
  - [ ] Focus ring appears (teal color)

- [ ] **Error State**
  - [ ] Input with `error` prop shows red border
  - [ ] Focus ring is red (destructive color)
  - [ ] `aria-invalid="true"` attribute present

- [ ] **Disabled State**
  - [ ] Disabled input not editable
  - [ ] Shows reduced opacity
  - [ ] Cursor changes to not-allowed

- [ ] **Accessibility**
  - [ ] Tab to input field
  - [ ] Type text
  - [ ] Error state announced by screen reader (aria-invalid)

### Card Component Testing

- [ ] **Basic Card**
  - [ ] Card renders with subtle shadow
  - [ ] Border visible
  - [ ] Background color correct for theme

- [ ] **Card Sections**
  - [ ] CardHeader renders correctly
  - [ ] CardTitle has proper font weight
  - [ ] CardDescription has muted color
  - [ ] CardContent has proper padding
  - [ ] CardFooter aligns items correctly

- [ ] **Nested Cards**
  - [ ] Cards can be nested
  - [ ] Shadows stack appropriately

### AppShell Layout Testing

- [ ] **Without Sidebar**
  - [ ] AppShell renders with just children
  - [ ] Navigation at top
  - [ ] Content area has proper max-width and padding

- [ ] **With Sidebar (Desktop >768px)**
  - [ ] Sidebar visible on left
  - [ ] Sidebar is sticky (scrolls independently)
  - [ ] Main content area flexes to remaining space
  - [ ] No horizontal scrolling

- [ ] **With Sidebar (Mobile <768px)**
  - [ ] Sidebar hidden by default
  - [ ] Floating toggle button visible (bottom-right)
  - [ ] Click toggle opens sidebar with slide animation
  - [ ] Overlay backdrop visible with blur
  - [ ] Click overlay closes sidebar
  - [ ] Close button inside sidebar works

- [ ] **Responsive Transitions**
  - [ ] Resize browser window
  - [ ] Verify smooth transitions at breakpoints
  - [ ] No layout shifts or jumps

### Theme System Integration

- [ ] **Data Attribute Support**
  - [ ] Verify `document.documentElement.dataset.theme` is set
  - [ ] Check both `[data-theme="dark"]` and `.dark` CSS selectors work
  - [ ] Confirm CSS variables update correctly

- [ ] **System Preference Listener**
  - [ ] Set theme to "system"
  - [ ] Change OS preference
  - [ ] Verify listener cleans up on unmount (check console for errors)

- [ ] **localStorage Integration**
  - [ ] Open Application tab in DevTools
  - [ ] Find localStorage key `skillforge-theme`
  - [ ] Toggle theme and verify key updates
  - [ ] Clear localStorage and verify default to "system"

### Cross-Browser Testing

- [ ] **Chrome/Edge**
  - [ ] All features work
  - [ ] Backdrop blur visible
  - [ ] CSS variables supported

- [ ] **Firefox**
  - [ ] All features work
  - [ ] Check OKLCH color support (should work)
  - [ ] Verify animations smooth

- [ ] **Safari**
  - [ ] All features work
  - [ ] Backdrop blur supported
  - [ ] Check for any layout quirks

- [ ] **Mobile Browsers (iOS Safari, Chrome Android)**
  - [ ] Theme toggle works
  - [ ] Sidebar toggle smooth
  - [ ] Touch interactions responsive

### Performance Testing

- [ ] **Initial Load**
  - [ ] Check Lighthouse performance score >90
  - [ ] Verify no layout shifts (CLS score)
  - [ ] Check First Contentful Paint <2s

- [ ] **Theme Toggle Performance**
  - [ ] Theme switch completes in <50ms
  - [ ] No flickering during transition
  - [ ] localStorage write doesn't block UI

- [ ] **Bundle Size**
  - [ ] Check dist folder after build
  - [ ] Main bundle ~380KB (~122KB gzipped)
  - [ ] No duplicate dependencies

### Accessibility Audit

- [ ] **Lighthouse Accessibility Score**
  - [ ] Run Lighthouse audit
  - [ ] Target score: 100
  - [ ] Fix any issues reported

- [ ] **Screen Reader Testing** (optional but recommended)
  - [ ] Enable VoiceOver (macOS) or NVDA (Windows)
  - [ ] Navigate through components
  - [ ] Verify all interactive elements announced
  - [ ] Check ARIA labels read correctly

- [ ] **Keyboard Navigation**
  - [ ] Tab through entire app
  - [ ] Verify focus order logical
  - [ ] All interactive elements reachable
  - [ ] No keyboard traps

- [ ] **Color Contrast**
  - [ ] Check all text meets WCAG AA (4.5:1 for normal text)
  - [ ] Verify teal primary color has sufficient contrast
  - [ ] Badge colors readable in both themes

## Component Showcase Testing

To test all components at once, you can create a showcase route:

1. Create a route at `/showcase` that renders `ComponentShowcase`
2. Navigate to `/showcase` in browser
3. Verify all components render correctly
4. Test interactions (buttons, inputs, theme toggle)
5. Check responsive behavior

## Known Issues / Warnings

- **PostCSS Warning:** "@import must precede all other statements"
  - Non-blocking, doesn't affect functionality
  - Can be resolved by reordering CSS imports

## Sign-Off Checklist

- [ ] All automated tests pass
- [ ] Manual testing completed for core features
- [ ] Tested in at least 2 browsers
- [ ] Responsive design verified on mobile/tablet/desktop
- [ ] Accessibility features working (keyboard nav, focus rings)
- [ ] Theme system persists correctly
- [ ] No console errors during normal usage
- [ ] Production build successful and deployed (if applicable)

## Test Environment

- Node version: v20+ (check with `node --version`)
- npm version: 11+ (check with `npm --version`)
- Browser versions tested:
  - Chrome: ___
  - Firefox: ___
  - Safari: ___
  - Mobile: ___

## Notes

Add any additional notes or observations during testing:

---

**Tester Name:** _______________
**Date Tested:** _______________
**Status:** [ ] PASS [ ] FAIL [ ] NEEDS REVISION
