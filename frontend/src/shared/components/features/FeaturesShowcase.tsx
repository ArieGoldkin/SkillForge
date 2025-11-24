/**
 * FeaturesShowcase - Comprehensive showcase for all feature components
 *
 * This component demonstrates all three feature component groups:
 * - Analysis (Progress, Steps, Activity Feed)
 * - Library (Skills, Search, Filters, Grid)
 * - Tutor (Chat, Messages, Code, Socratic Prompts)
 *
 * Use this for visual testing and documentation.
 */

import * as React from 'react'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/components/ui/tabs'

import { AnalysisTab, LibraryTab, TutorTab } from './showcase'

/**
 * FeaturesShowcase component
 *
 * Simplified main component that delegates to specialized tab components.
 * Each tab is responsible for its own demo data and component showcase.
 */
export const FeaturesShowcase: React.FC = () => {
  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <div>
          <h1 className="text-4xl font-bold mb-2">Feature Components Showcase</h1>
          <p className="text-muted-foreground">
            Visual testing and documentation for all SkillForge feature components
          </p>
        </div>

        <Tabs defaultValue="analysis" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="analysis">Analysis</TabsTrigger>
            <TabsTrigger value="library">Library</TabsTrigger>
            <TabsTrigger value="tutor">Tutor</TabsTrigger>
          </TabsList>

          <TabsContent value="analysis" className="space-y-6">
            <AnalysisTab />
          </TabsContent>

          <TabsContent value="library" className="space-y-6">
            <LibraryTab />
          </TabsContent>

          <TabsContent value="tutor" className="space-y-6">
            <TutorTab />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

FeaturesShowcase.displayName = 'FeaturesShowcase'
