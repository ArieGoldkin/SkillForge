import { AppShell } from '@/shared/components/layout'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Input } from '@/shared/components/ui/input'

/**
 * Component Showcase
 *
 * Demonstrates all customized components with SkillForge design tokens.
 * Use this as a reference for component usage and styling.
 */
export function ComponentShowcase() {
  const sidebar = (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-sidebar-foreground">Sidebar Navigation</h3>
      <nav className="space-y-2">
        <a
          href="#buttons"
          className="block rounded-md px-3 py-2 text-sm text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
        >
          Buttons
        </a>
        <a
          href="#badges"
          className="block rounded-md px-3 py-2 text-sm text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
        >
          Badges
        </a>
        <a
          href="#inputs"
          className="block rounded-md px-3 py-2 text-sm text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
        >
          Inputs
        </a>
        <a
          href="#cards"
          className="block rounded-md px-3 py-2 text-sm text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
        >
          Cards
        </a>
      </nav>
    </div>
  )

  return (
    <AppShell sidebar={sidebar} showSidebar>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-foreground">Component Showcase</h1>
          <p className="mt-2 text-muted-foreground">
            Explore all customized shadcn/ui components with SkillForge design tokens
          </p>
        </div>

        {/* Buttons Section */}
        <section id="buttons">
          <Card>
            <CardHeader>
              <CardTitle>Buttons</CardTitle>
              <CardDescription>All button variants with teal focus states</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Button variant="default">Default</Button>
                <Button variant="teal">Teal Accent</Button>
                <Button variant="secondary">Secondary</Button>
                <Button variant="destructive">Destructive</Button>
                <Button variant="outline">Outline</Button>
                <Button variant="ghost">Ghost</Button>
                <Button variant="link">Link</Button>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button size="sm">Small</Button>
                <Button size="default">Default</Button>
                <Button size="lg">Large</Button>
                <Button size="icon">🚀</Button>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button disabled>Disabled</Button>
                <Button variant="teal" disabled>
                  Disabled Teal
                </Button>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Badges Section */}
        <section id="badges">
          <Card>
            <CardHeader>
              <CardTitle>Badges</CardTitle>
              <CardDescription>Status badges with semantic colors</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Badge variant="default">Default</Badge>
                <Badge variant="secondary">Secondary</Badge>
                <Badge variant="destructive">Destructive</Badge>
                <Badge variant="outline">Outline</Badge>
              </div>

              <div className="flex flex-wrap gap-2">
                <Badge variant="success">Success</Badge>
                <Badge variant="warning">Warning</Badge>
                <Badge variant="error">Error</Badge>
                <Badge variant="info">Info</Badge>
              </div>

              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Use cases:</p>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="success">Completed</Badge>
                  <Badge variant="warning">In Progress</Badge>
                  <Badge variant="error">Failed</Badge>
                  <Badge variant="info">Pending</Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Inputs Section */}
        <section id="inputs">
          <Card>
            <CardHeader>
              <CardTitle>Inputs</CardTitle>
              <CardDescription>Text inputs with teal focus ring and error states</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="normal-input" className="text-sm font-medium">
                  Normal Input
                </label>
                <Input id="normal-input" type="text" placeholder="Enter text..." />
              </div>

              <div className="space-y-2">
                <label htmlFor="error-input" className="text-sm font-medium text-destructive">
                  Input with Error
                </label>
                <Input
                  id="error-input"
                  type="text"
                  placeholder="Invalid input"
                  error
                  defaultValue="invalid@"
                />
                <p className="text-xs text-destructive">This field contains errors</p>
              </div>

              <div className="space-y-2">
                <label htmlFor="disabled-input" className="text-sm font-medium">
                  Disabled Input
                </label>
                <Input
                  id="disabled-input"
                  type="text"
                  placeholder="Disabled"
                  disabled
                  defaultValue="Cannot edit"
                />
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Cards Section */}
        <section id="cards">
          <Card>
            <CardHeader>
              <CardTitle>Cards</CardTitle>
              <CardDescription>Card components with SkillForge shadows and borders</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Simple Card</CardTitle>
                    <CardDescription>A basic card component</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm">
                      Cards use subtle shadows and borders from SkillForge design tokens.
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Nested Card</CardTitle>
                    <CardDescription>Cards can be nested</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm">The design system supports multiple levels of depth.</p>
                  </CardContent>
                </Card>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Theme Demo */}
        <section>
          <Card>
            <CardHeader>
              <CardTitle>Theme System</CardTitle>
              <CardDescription>
                Use the theme toggle in the navigation to switch between light, dark, and system
                themes
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-lg border border-border bg-muted p-4">
                <p className="text-sm">
                  The theme toggle cycles through three states: Light → Dark → System
                </p>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium">Theme Persistence:</p>
                <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
                  <li>Theme preference is saved to localStorage</li>
                  <li>Persists across page reloads and sessions</li>
                  <li>System mode follows OS preference automatically</li>
                  <li>Uses data-theme attribute for styling</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </AppShell>
  )
}
