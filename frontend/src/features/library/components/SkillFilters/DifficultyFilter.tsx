/**
 * DifficultyFilter - Difficulty level filter section
 */

import type * as React from 'react'

import type { SkillDifficulty } from '../SkillCard'

import { CheckboxItem } from './CheckboxItem'
import { FilterSection } from './FilterSection'

/**
 * Props for DifficultyFilter component
 */
export interface DifficultyFilterProps {
  selectedDifficulties: SkillDifficulty[]
  onChange: (difficulty: SkillDifficulty, checked: boolean) => void
}

/**
 * Available difficulty levels
 */
const difficulties: SkillDifficulty[] = ['beginner', 'intermediate', 'advanced']

/**
 * DifficultyFilter component
 *
 * Provides checkboxes for filtering by skill difficulty level.
 */
export const DifficultyFilter: React.FC<DifficultyFilterProps> = ({
  selectedDifficulties,
  onChange,
}) => {
  return (
    <FilterSection title="Difficulty">
      {difficulties.map((difficulty) => (
        <CheckboxItem
          key={difficulty}
          id={`difficulty-${difficulty}`}
          label={difficulty}
          checked={selectedDifficulties.includes(difficulty)}
          onChange={(checked) => onChange(difficulty, checked)}
        />
      ))}
    </FilterSection>
  )
}

DifficultyFilter.displayName = 'DifficultyFilter'
