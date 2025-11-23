import { createFileRoute } from '@tanstack/react-router'

import { FeaturesShowcase } from '@/components/features/FeaturesShowcase'

/**
 * Showcase Route - Component Testing & Documentation
 *
 * This route displays all UI components for development and testing purposes.
 * Use this page to:
 * - Visually test all components in isolation
 * - Verify theme switching (light/dark/system)
 * - Test responsive behavior
 * - Demonstrate component variations
 *
 * Access: http://localhost:5173/showcase
 */
export const Route = createFileRoute('/showcase')({
  component: ShowcasePage,
})

function ShowcasePage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">SkillForge Component Showcase</h1>
        <p className="text-muted-foreground">
          Development testing environment for Phase 3 feature components
        </p>
        <p className="text-sm text-muted-foreground mt-2">
          💡 Use the theme toggle in the navigation to test light/dark/system modes
        </p>
      </div>
      <FeaturesShowcase />
    </div>
  )
}
