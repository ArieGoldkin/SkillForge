import { useState } from 'react'

import { useNavigate } from '@tanstack/react-router'

import { analyzeAPI } from '@services/api.service'

import { FeaturesSection } from './components/FeaturesSection'
import { HeroSection } from './components/HeroSection'
import { HowItWorksSection } from './components/HowItWorksSection'

type ContentType = 'article' | 'video' | 'repository'

export default function Home() {
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedContentType, setSelectedContentType] = useState<ContentType>('article')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return

    setIsSubmitting(true)
    setError(null)
    try {
      // Use real backend API
      const response = await analyzeAPI.createAnalysis({ url })
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
        isSubmitting={isSubmitting}
        handleSubmit={handleSubmit}
        error={error}
      />
      <FeaturesSection />
      <HowItWorksSection />
    </div>
  )
}
