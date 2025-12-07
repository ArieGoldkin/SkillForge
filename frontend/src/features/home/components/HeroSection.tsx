import { AlertCircle, FileText, Github, Link, Sparkles, Video } from 'lucide-react'

import { Alert, AlertDescription } from '@shared/components/ui/alert'
import { Badge } from '@shared/components/ui/badge'
import { Button } from '@shared/components/ui/button'
import { Input } from '@shared/components/ui/input'
import { SkillLevelSelector } from '@shared/SkillLevelSelector'
import type { SkillLevel } from '@shared/SkillLevelSelector'

import { cn } from '@lib/utils'

type ContentType = 'article' | 'video' | 'repository'

interface HeroSectionProps {
  url: string
  setUrl: (url: string) => void
  selectedContentType: ContentType
  setSelectedContentType: (type: ContentType) => void
  skillLevel: SkillLevel
  setSkillLevel: (level: SkillLevel) => void
  isSubmitting: boolean
  handleSubmit: (e: React.FormEvent) => void
  error?: string | null
}

export function HeroSection({
  url,
  setUrl,
  selectedContentType,
  setSelectedContentType,
  skillLevel,
  setSkillLevel,
  isSubmitting,
  handleSubmit,
  error,
}: HeroSectionProps) {
  return (
    <section className="py-20 px-8">
      <div className="max-w-4xl mx-auto text-center">
        <h1 className="text-5xl md:text-6xl font-bold mb-6">
          Intelligent Learning
          <br />
          Integration Platform
        </h1>
        <p className="text-xl text-muted-foreground mb-12">
          Analyze technical content and generate AI-ready implementation guides with expert tutoring
        </p>

        <ContentAnalysisForm
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
      </div>
    </section>
  )
}

interface ContentAnalysisFormProps {
  url: string
  setUrl: (url: string) => void
  selectedContentType: ContentType
  setSelectedContentType: (type: ContentType) => void
  skillLevel: SkillLevel
  setSkillLevel: (level: SkillLevel) => void
  isSubmitting: boolean
  handleSubmit: (e: React.FormEvent) => void
  error?: string | null
}

function ContentAnalysisForm({
  url,
  setUrl,
  selectedContentType,
  setSelectedContentType,
  skillLevel,
  setSkillLevel,
  isSubmitting,
  handleSubmit,
  error,
}: ContentAnalysisFormProps) {
  return (
    <form onSubmit={handleSubmit} className="max-w-2xl mx-auto mb-8">
      <div className="relative">
        <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none">
          <Link className="w-5 h-5 text-muted-foreground" />
        </div>
        <Input
          type="url"
          placeholder="Enter URL, video link, or repository..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="pl-12 h-14 text-base"
          required
        />
      </div>

      <ContentTypeBadges
        selectedContentType={selectedContentType}
        setSelectedContentType={setSelectedContentType}
      />

      <SkillLevelSelector value={skillLevel} onChange={setSkillLevel} />

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Button type="submit" disabled={isSubmitting || !url.trim()} size="lg" className="gap-2">
        <Sparkles className="w-5 h-5" />
        {isSubmitting ? 'Analyzing...' : 'Analyze Content'}
      </Button>
    </form>
  )
}

interface ContentTypeBadgesProps {
  selectedContentType: ContentType
  setSelectedContentType: (type: ContentType) => void
}

function ContentTypeBadges({
  selectedContentType,
  setSelectedContentType,
}: ContentTypeBadgesProps) {
  return (
    <div className="flex justify-center gap-3 my-6">
      <ContentTypeBadge
        type="article"
        icon={FileText}
        label="Article"
        selected={selectedContentType === 'article'}
        onClick={() => setSelectedContentType('article')}
      />
      <ContentTypeBadge
        type="video"
        icon={Video}
        label="Video"
        selected={selectedContentType === 'video'}
        onClick={() => setSelectedContentType('video')}
      />
      <ContentTypeBadge
        type="repository"
        icon={Github}
        label="Repository"
        selected={selectedContentType === 'repository'}
        onClick={() => setSelectedContentType('repository')}
      />
    </div>
  )
}

interface ContentTypeBadgeProps {
  type: ContentType
  icon: React.ComponentType<{ className?: string }>
  label: string
  selected: boolean
  onClick: () => void
}

function ContentTypeBadge({ icon: Icon, label, selected, onClick }: ContentTypeBadgeProps) {
  return (
    <Badge
      variant={selected ? 'default' : 'outline'}
      className={cn(
        'cursor-pointer transition-all hover:scale-105 px-4 py-2 gap-2',
        selected && 'ring-2 ring-ring ring-offset-2'
      )}
      onClick={onClick}
    >
      <Icon className="w-4 h-4" />
      {label}
    </Badge>
  )
}
