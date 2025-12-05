/**
 * Skill Level Selector Component
 * Allows users to select their experience level for personalized analysis output
 */

export type SkillLevel = 'beginner' | 'intermediate' | 'expert'

interface SkillLevelSelectorProps {
  value: SkillLevel
  onChange: (level: SkillLevel) => void
}

const SKILL_LEVELS: { value: SkillLevel; label: string; description: string; icon: string }[] = [
  {
    value: 'beginner',
    label: 'Beginner',
    description: 'New to development, need detailed explanations',
    icon: '🌱',
  },
  {
    value: 'intermediate',
    label: 'Intermediate',
    description: 'Familiar with concepts, seeking best practices',
    icon: '🚀',
  },
  {
    value: 'expert',
    label: 'Expert',
    description: 'Advanced developer, want concise insights',
    icon: '⚡',
  },
]

export function SkillLevelSelector({ value, onChange }: SkillLevelSelectorProps) {
  return (
    <div className="skill-level-selector">
      <label className="skill-level-label">Your Experience Level</label>
      <div className="skill-level-options">
        {SKILL_LEVELS.map((level) => (
          <button
            key={level.value}
            type="button"
            className={`skill-level-option ${value === level.value ? ' skill-level-option--active' : ''}`}
            onClick={() => onChange(level.value)}
            aria-pressed={value === level.value}
          >
            <span className="skill-level-icon">{level.icon}</span>
            <span className="skill-level-text">
              <strong>{level.label}</strong>
              <small>{level.description}</small>
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
