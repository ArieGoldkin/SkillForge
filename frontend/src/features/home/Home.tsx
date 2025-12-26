import { useActionState, useState } from 'react'

import { useNavigate } from '@tanstack/react-router'

import { ReactScanTest } from '@/components/ReactScanTest'
import { logger } from '@/lib/logger'

import type { AnalysisMode } from '@shared/AnalysisModeSelector'
import type { SkillLevel } from '@shared/SkillLevelSelector'

import { analyzeAPI } from '@services/api.service'

import { FeaturesSection } from './components/FeaturesSection'
import { HeroSection } from './components/HeroSection'
import { HowItWorksSection } from './components/HowItWorksSection'

type ContentType = 'article' | 'video' | 'repository'

interface AnalysisState {
  success: boolean
  error: string | null
  analysisId?: string
}

interface AnalysisFormData {
  url: string
  skillLevel: SkillLevel
  analysisMode: AnalysisMode
}

// eslint-disable-next-line max-lines-per-function -- Component handles URL input, content type selection, skill level selection, form validation, API calls, and error handling
export default function Home() {
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [selectedContentType, setSelectedContentType] = useState<ContentType>('article')
  const [skillLevel, setSkillLevel] = useState<SkillLevel>('intermediate')
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>('standard')

  const [state, submitAction] = useActionState<AnalysisState, AnalysisFormData>(
    async (_prevState, formData) => {
      try {
        logger.info('Creating analysis', {
          url: formData.url,
          skillLevel: formData.skillLevel,
          analysisMode: formData.analysisMode,
        })

        const response = await analyzeAPI.createAnalysis({
          url: formData.url,
          skill_level: formData.skillLevel,
          analysis_mode: formData.analysisMode,
        })

        logger.info('Analysis created, navigating', {
          analysisId: response.analysis_id,
          sseEndpoint: response.sse_endpoint,
          status: response.status,
        })

        // Navigate to analysis page
        const targetPath = `/analyze/${response.analysis_id}`
        logger.info('Navigating to', { targetPath, analysisId: response.analysis_id })

        try {
          navigate({ to: '/analyze/$id', params: { id: response.analysis_id } })
          logger.info('Navigation called', { analysisId: response.analysis_id })
        } catch (navError) {
          logger.error('Navigation failed', {
            error: navError instanceof Error ? navError.message : String(navError),
            analysisId: response.analysis_id,
            stack: navError instanceof Error ? navError.stack : undefined,
          })
          // Fallback to window.location if router navigation fails
          window.location.href = targetPath
        }

        return { success: true, error: null, analysisId: response.analysis_id }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create analysis'
        logger.error('Failed to create analysis', {
          error: err instanceof Error ? err.message : String(err),
          url: formData.url,
          skillLevel: formData.skillLevel,
          stack: err instanceof Error ? err.stack : undefined,
        })
        return { success: false, error: message }
      }
    },
    { success: false, error: null }
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return

    submitAction({
      url,
      skillLevel,
      analysisMode,
    })
  }

  return (
    <div className="flex flex-col">
      <HeroSection
        url={url}
        setUrl={setUrl}
        selectedContentType={selectedContentType}
        setSelectedContentType={setSelectedContentType}
        skillLevel={skillLevel}
        setSkillLevel={setSkillLevel}
        analysisMode={analysisMode}
        setAnalysisMode={setAnalysisMode}
        handleSubmit={handleSubmit}
        error={state.error}
      />
      <FeaturesSection />
      <HowItWorksSection />

      {/* React Scan Performance Test (development only) */}
      {import.meta.env.DEV && (
        <div className="container mx-auto px-4 py-8">
          <ReactScanTest />
        </div>
      )}
    </div>
  )
}
