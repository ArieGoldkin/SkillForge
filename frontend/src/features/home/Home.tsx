import { useState } from 'react'

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

// eslint-disable-next-line max-lines-per-function -- Component handles URL input, content type selection, skill level selection, form validation, API calls, and error handling
export default function Home() {
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedContentType, setSelectedContentType] = useState<ContentType>('article')
  const [skillLevel, setSkillLevel] = useState<SkillLevel>('intermediate')
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>('standard')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return

    setIsSubmitting(true)
    setError(null)
    try {
      // Use real backend API with skill level and analysis mode
      logger.info('Creating analysis', { url, skillLevel, analysisMode })
      const response = await analyzeAPI.createAnalysis({
        url,
        skill_level: skillLevel,
        analysis_mode: analysisMode,
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
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create analysis'
      setError(message)
      logger.error('Failed to create analysis', {
        error: err instanceof Error ? err.message : String(err),
        url,
        skillLevel,
        stack: err instanceof Error ? err.stack : undefined,
      })
    } finally {
      setIsSubmitting(false)
    }
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
        isSubmitting={isSubmitting}
        handleSubmit={handleSubmit}
        error={error}
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
