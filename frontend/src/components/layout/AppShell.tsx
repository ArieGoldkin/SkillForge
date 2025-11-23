import { type ReactNode, useState } from 'react'

import { Menu, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { Navigation } from '@/shared/components/Navigation'

interface AppShellProps {
  children: ReactNode
  sidebar?: ReactNode
  showSidebar?: boolean
}

/**
 * AppShell Layout Component
 *
 * Main application layout wrapper providing:
 * - Sticky navigation header
 * - Optional collapsible sidebar
 * - Main content area
 *
 * Features:
 * - Responsive design (sidebar collapses on mobile)
 * - Smooth transitions
 * - Semantic HTML structure
 * - Proper ARIA labels for accessibility
 *
 * Usage:
 * ```tsx
 * <AppShell sidebar={<Sidebar />} showSidebar>
 *   <PageContent />
 * </AppShell>
 * ```
 */
export function AppShell({ children, sidebar, showSidebar = false }: AppShellProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  const toggleSidebar = () => setIsSidebarOpen((prev) => !prev)

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Navigation Header */}
      <Navigation />

      {/* Main Content Wrapper */}
      <div className="relative flex min-h-[calc(100vh-4rem)]">
        {/* Sidebar - Only render if sidebar content is provided and showSidebar is true */}
        {showSidebar && sidebar && (
          <>
            {/* Mobile Sidebar Overlay */}
            {isSidebarOpen && (
              <div
                className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm md:hidden"
                onClick={toggleSidebar}
                aria-hidden="true"
              />
            )}

            {/* Sidebar */}
            <aside
              className={cn(
                'fixed inset-y-0 left-0 top-16 z-50 w-64 border-r border-border bg-sidebar transition-transform duration-300 ease-in-out md:sticky md:translate-x-0',
                isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
              )}
              aria-label="Sidebar navigation"
            >
              {/* Mobile Close Button */}
              <div className="flex items-center justify-end p-4 md:hidden">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleSidebar}
                  aria-label="Close sidebar"
                >
                  <X className="h-5 w-5" />
                </Button>
              </div>

              {/* Sidebar Content */}
              <div className="overflow-y-auto px-4 pb-4">{sidebar}</div>
            </aside>

            {/* Mobile Sidebar Toggle Button */}
            <Button
              variant="ghost"
              size="icon"
              className="fixed bottom-4 right-4 z-40 shadow-lg md:hidden"
              onClick={toggleSidebar}
              aria-label="Toggle sidebar"
              aria-expanded={isSidebarOpen}
            >
              <Menu className="h-5 w-5" />
            </Button>
          </>
        )}

        {/* Main Content Area */}
        <main className="flex-1 overflow-x-hidden">
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</div>
        </main>
      </div>
    </div>
  )
}
