import { useState } from 'react'

import { useNavigate } from '@tanstack/react-router'

import type { SkillLevel } from '@shared/SkillLevelSelector'

import { analyzeAPI } from '@services/api.service'

import { FeaturesSection } from './components/FeaturesSection'
import { HeroSection } from './components/HeroSection'
import { HowItWorksSection } from './components/HowItWorksSection'

// React Scan test component (development only)
import { ReactScanTest } from '@components/ReactScanTest'

type ContentType = 'article' | 'video' | 'repository'

export default function Home() {
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedContentType, setSelectedContentType] = useState<ContentType>('article')
  const [skillLevel, setSkillLevel] = useState<SkillLevel>('intermediate')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return

    setIsSubmitting(true)
    setError(null)
    try {
      // Use real backend API with skill level
      const response = await analyzeAPI.createAnalysis({ url, skill_level: skillLevel })
      navigate({ to: '/analyze/$id', params: { id: response.analysis_id } })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create analysis'
      setError(message)
      console.error('Failed to create analysis:', err)
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
