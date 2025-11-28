import * as React from 'react'

import { ChevronDown, ChevronUp, Lightbulb } from 'lucide-react'

import { Badge } from '@shared/components/ui/badge'
import { Button } from '@shared/components/ui/button'

import { cn } from '@lib/utils'

/**
 * Difficulty level for Socratic questions
 */
export type SocraticDifficulty = 'easy' | 'medium' | 'hard'

/**
 * Props for SocraticPrompt component
 */
export interface SocraticPromptProps {
  question: string
  hints?: string[]
  difficulty: SocraticDifficulty
  className?: string
}

/**
 * Get badge variant for difficulty
 */
const getDifficultyVariant = (
  difficulty: SocraticDifficulty
): 'success' | 'warning' | 'destructive' => {
  const variants: Record<SocraticDifficulty, 'success' | 'warning' | 'destructive'> = {
    easy: 'success',
    medium: 'warning',
    hard: 'destructive',
  }
  return variants[difficulty]
}

/**
 * SocraticPrompt - Formatted Socratic question from tutor
 *
 * Displays a Socratic-style question with distinct visual styling, difficulty badge,
 * and expandable hints section. Designed to encourage critical thinking.
 *
 * @example
 * ```tsx
 * <SocraticPrompt
 *   question="What challenges arise when React components execute only in the browser?"
 *   hints={[
 *     "Consider data fetching requirements",
 *     "Think about bundle size implications",
 *     "What about server-only resources?"
 *   ]}
 *   difficulty="medium"
 * />
 * ```
 */
/* eslint-disable max-lines-per-function -- Component requires complete Socratic prompt layout (header with icon/difficulty, question text, expandable hints section with toggle button, hint list). Interactive state management and conditional rendering necessitate current structure. */
export const SocraticPrompt: React.FC<SocraticPromptProps> = ({
  question,
  hints = [],
  difficulty,
  className,
}) => {
  const [showHints, setShowHints] = React.useState(false)

  const processedHints = React.useMemo(
    () => hints.map((content, idx) => ({ id: `hint-${idx + 1}`, number: idx + 1, content })),
    [hints]
  )

  const toggleHints = () => {
    setShowHints((prev) => !prev)
  }

  return (
    <div
      className={cn(
        'my-4 rounded-lg border-l-4 border-l-primary bg-accent/5 p-4',
        'animate-in slide-in-from-left-2 duration-300',
        className
      )}
      role="article"
      aria-label="Socratic question"
    >
      {/* Header with icon and difficulty */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-start gap-2">
          <Lightbulb className="h-5 w-5 text-primary mt-0.5 shrink-0" aria-hidden="true" />
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                Think About This
              </span>
              <Badge variant={getDifficultyVariant(difficulty)} className="text-xs capitalize">
                {difficulty}
              </Badge>
            </div>
          </div>
        </div>
      </div>

      {/* Question */}
      <p className="text-sm leading-relaxed mb-3 font-medium">{question}</p>

      {/* Hints section */}
      {hints.length > 0 && (
        <div className="mt-4 pt-3 border-t border-border">
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleHints}
            className="h-8 px-2 -ml-2 gap-1 hover:bg-accent"
            aria-expanded={showHints}
            aria-controls="hints-content"
          >
            {showHints ? (
              <>
                <ChevronUp className="h-4 w-4" />
                <span className="text-xs font-medium">Hide hints</span>
              </>
            ) : (
              <>
                <ChevronDown className="h-4 w-4" />
                <span className="text-xs font-medium">Show hints ({hints.length})</span>
              </>
            )}
          </Button>

          {showHints && (
            <div
              id="hints-content"
              className="mt-3 space-y-2 animate-in slide-in-from-top-2 duration-200"
            >
              {processedHints.map((hint) => (
                <div key={hint.id} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-semibold">
                    {hint.number}
                  </span>
                  <p className="flex-1 leading-relaxed">{hint.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

SocraticPrompt.displayName = 'SocraticPrompt'
