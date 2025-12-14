/**
 * TopicList - Radio button list for topic selection
 * Issue #114: Topic Selection Modal
 */

import { Label } from '@shared/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@shared/components/ui/radio-group'

import { cn } from '@lib/utils'

import type { TutoringTopic } from './types'

interface TopicListProps {
  topics: TutoringTopic[]
  selectedId: string | null
  onSelect: (id: string) => void
}

export function TopicList({ topics, selectedId, onSelect }: TopicListProps) {
  return (
    <RadioGroup value={selectedId ?? undefined} onValueChange={onSelect} className="space-y-2">
      {topics.map((topic) => (
        <Label
          key={topic.id}
          htmlFor={topic.id}
          className={cn(
            'flex items-start gap-3 rounded-lg border p-4 cursor-pointer transition-colors',
            selectedId === topic.id
              ? 'border-primary bg-primary/5'
              : 'border-border hover:border-primary/50 hover:bg-muted/50'
          )}
        >
          <RadioGroupItem value={topic.id} id={topic.id} className="mt-0.5" />
          <div className="flex-1">
            <span className="text-sm font-medium">{topic.name}</span>
            {topic.description && (
              <p className="text-xs text-muted-foreground mt-1">{topic.description}</p>
            )}
          </div>
        </Label>
      ))}
    </RadioGroup>
  )
}
