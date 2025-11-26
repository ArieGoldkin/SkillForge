/**
 * SkillForge Design System Example
 *
 * This example demonstrates how to use the design system tokens
 * and shadcn/ui components together.
 *
 * Usage: Import this component to see the design system in action
 */

import { Badge } from '@shared/components/ui/badge'
import { Button } from '@shared/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@shared/components/ui/card'
import { Input } from '@shared/components/ui/input'
import { Progress } from '@shared/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@shared/components/ui/tabs'

export function DesignSystemExample() {
  return (
    <div className="min-h-screen bg-background p-8">
      <div className="mx-auto max-w-4xl space-y-8">
        {/* Header */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold text-foreground">SkillForge Design System</h1>
          <p className="text-lg text-muted-foreground">
            Clean modern design with teal accents and OKLCH colors
          </p>
        </div>

        {/* Color Palette Card */}
        <Card>
          <CardHeader>
            <CardTitle>Color Palette</CardTitle>
            <CardDescription>OKLCH perceptually uniform colors</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <div className="space-y-2">
                <div className="h-16 rounded-lg bg-primary" />
                <p className="text-sm font-medium">Primary (Teal)</p>
              </div>
              <div className="space-y-2">
                <div className="h-16 rounded-lg bg-secondary" />
                <p className="text-sm font-medium">Secondary</p>
              </div>
              <div className="space-y-2">
                <div className="h-16 rounded-lg bg-accent" />
                <p className="text-sm font-medium">Accent</p>
              </div>
              <div className="space-y-2">
                <div className="h-16 rounded-lg bg-destructive" />
                <p className="text-sm font-medium">Destructive</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Buttons Card */}
        <Card>
          <CardHeader>
            <CardTitle>Button Variants</CardTitle>
            <CardDescription>All available button styles</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-4">
            <Button>Default</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="destructive">Destructive</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="link">Link</Button>
          </CardContent>
        </Card>

        {/* Form Example */}
        <Card>
          <CardHeader>
            <CardTitle>Form Elements</CardTitle>
            <CardDescription>Input fields with focus states</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium">
                Email
              </label>
              <Input id="email" type="email" placeholder="you@example.com" />
            </div>
            <div className="space-y-2">
              <label htmlFor="name" className="text-sm font-medium">
                Name
              </label>
              <Input id="name" type="text" placeholder="John Doe" />
            </div>
          </CardContent>
          <CardFooter>
            <Button>Submit</Button>
          </CardFooter>
        </Card>

        {/* Tabs Example */}
        <Card>
          <CardHeader>
            <CardTitle>Tabs Component</CardTitle>
            <CardDescription>Organized content sections</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="overview">
              <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="features">Features</TabsTrigger>
                <TabsTrigger value="progress">Progress</TabsTrigger>
              </TabsList>
              <TabsContent value="overview" className="space-y-4">
                <p className="text-muted-foreground">
                  SkillForge is an intelligent learning integration platform that helps you master
                  new technologies.
                </p>
                <div className="flex gap-2">
                  <Badge>React 19</Badge>
                  <Badge variant="secondary">TypeScript</Badge>
                  <Badge variant="outline">Tailwind CSS</Badge>
                </div>
              </TabsContent>
              <TabsContent value="features">
                <ul className="space-y-2 text-muted-foreground">
                  <li>• AI-powered content analysis</li>
                  <li>• Interactive learning paths</li>
                  <li>• Progress tracking</li>
                  <li>• Socratic tutoring</li>
                </ul>
              </TabsContent>
              <TabsContent value="progress" className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Learning Progress</span>
                    <span className="text-muted-foreground">75%</span>
                  </div>
                  <Progress value={75} />
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Typography Card */}
        <Card>
          <CardHeader>
            <CardTitle>Typography</CardTitle>
            <CardDescription>Outfit font family with variable weights</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h1 className="text-4xl font-bold">Heading 1 (48px)</h1>
              <h2 className="text-2xl font-bold">Heading 2 (32px)</h2>
              <h3 className="text-xl font-semibold">Heading 3 (24px)</h3>
              <p className="text-base">Body text (16px) with normal weight</p>
              <p className="text-sm text-muted-foreground">Small text (14px) muted</p>
              <p className="text-xs text-muted-foreground">Extra small text (12px) muted</p>
            </div>
          </CardContent>
        </Card>

        {/* Shadow Examples */}
        <Card>
          <CardHeader>
            <CardTitle>Elevation & Shadows</CardTitle>
            <CardDescription>Subtle depth perception with shadow utilities</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
              <div className="rounded-lg bg-card p-4 shadow-sm">
                <p className="text-sm font-medium">Shadow SM</p>
              </div>
              <div className="rounded-lg bg-card p-4 shadow-md">
                <p className="text-sm font-medium">Shadow MD</p>
              </div>
              <div className="rounded-lg bg-card p-4 shadow-lg">
                <p className="text-sm font-medium">Shadow LG</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
