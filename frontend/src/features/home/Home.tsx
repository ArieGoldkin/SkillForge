import { useState } from 'react'

import { useNavigate } from '@tanstack/react-router'

import { mockAnalyzeAPI } from '@services/mock.service'

import { FeaturesSection } from './components/FeaturesSection'
import { HeroSection } from './components/HeroSection'
import { HowItWorksSection } from './components/HowItWorksSection'

type ContentType = 'article' | 'video' | 'repository'

export default function Home() {
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [selectedContentType, setSelectedContentType] = useState<ContentType>('article')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return

    setIsSubmitting(true)
    try {
      const response = await mockAnalyzeAPI.createAnalysis({ url })
      navigate({ to: '/analyze/$id', params: { id: response.analysis_id } })
    } catch (error) {
      console.error('Failed to create analysis:', error)
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
      />
      <FeaturesSection />
      <HowItWorksSection />
    </div>
  )
}
