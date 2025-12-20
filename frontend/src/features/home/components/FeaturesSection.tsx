import { BookOpen, Bot, Library, MessageCircle } from 'lucide-react'

import { UI_CONSTANTS } from '@/lib/constants'

import { Card, CardContent } from '@shared/components/ui/card'

interface FeatureCardProps {
  icon: React.ComponentType<{ className?: string }>
  title: string
  description: string
}

function FeatureCard({ icon: Icon, title, description }: FeatureCardProps) {
  return (
    <Card className="text-center transition-all hover:-translate-y-2">
      <CardContent className="p-8">
        <div className="mb-4 text-primary">
          <Icon className={`${UI_CONSTANTS.ICON_SIZE_LG} mx-auto`} />
        </div>
        <h3 className="text-xl font-semibold mb-3">{title}</h3>
        <p className="text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  )
}

export function FeaturesSection() {
  const features = [
    {
      icon: Bot,
      title: 'Multi-Agent Analysis',
      description: '8 specialized agents analyze content from multiple perspectives',
    },
    {
      icon: BookOpen,
      title: 'Implementation Guides',
      description: 'AI-ready markdown guides with code examples and best practices',
    },
    {
      icon: MessageCircle,
      title: 'Socratic Tutoring',
      description: 'Interactive AI tutor guides you through implementation step-by-step',
    },
    {
      icon: Library,
      title: 'Library Management',
      description: 'Save, organize, and search your analyzed content and guides',
    },
  ]

  return (
    <section
      className={`${UI_CONSTANTS.PADDING_Y_MD} ${UI_CONSTANTS.PADDING_X_MD} ${UI_CONSTANTS.BG_MUTED_OPACITY}`}
    >
      <div className={`${UI_CONSTANTS.LAYOUT_MAX_WIDTH_7XL} ${UI_CONSTANTS.LAYOUT_MARGIN_X_AUTO}`}>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature) => (
            <FeatureCard key={feature.title} {...feature} />
          ))}
        </div>
      </div>
    </section>
  )
}
