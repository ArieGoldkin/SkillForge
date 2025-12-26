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

import type * as React from 'react'

import { UI_CONSTANTS } from '@/lib/constants'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@shared/components/ui/tabs'

import { AnalysisTab } from './AnalysisTab'
import { LibraryTab } from './LibraryTab'
import { TutorTab } from './TutorTab'

/**
 * FeaturesShowcase component
 *
 * Simplified main component that delegates to specialized tab components.
 * Each tab is responsible for its own demo data and component showcase.
 */
export function FeaturesShowcase(): React.ReactNode {
  return (
    <div className="min-h-screen bg-background p-8">
      <div
        className={`${UI_CONSTANTS.LAYOUT_MAX_WIDTH_7XL} ${UI_CONSTANTS.LAYOUT_MARGIN_X_AUTO} space-y-8`}
      >
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
