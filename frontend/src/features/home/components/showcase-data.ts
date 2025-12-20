/**
 * Demo data for FeaturesShowcase component
 *
 * This file contains all static demo data used in the feature showcase.
 * Data generation functions use factory patterns to ensure deterministic
 * initialization (avoiding React purity violations).
 */

import { DEMO_CONSTANTS } from '@/lib/constants'

import type { AgentActivity, AnalysisStep } from '@features/analysis/components'
import type { SkillCardProps } from '@features/library/components'

/**
 * Factory function to create analysis step demo data
 * Wraps Date.now() calls to avoid React purity violations
 */
export const createAnalysisSteps = (): AnalysisStep[] => [
  {
    id: '1',
    title: 'Extracting Content',
    description: 'Fetching and parsing content from URL',
    status: 'completed',
    timestamp: new Date(Date.now() - DEMO_CONSTANTS.TIME_OFFSET_5_MINUTES),
    duration: DEMO_CONSTANTS.TIME_OFFSET_5_SECONDS,
  },
  {
    id: '2',
    title: 'Multi-Agent Analysis',
    description: 'Running specialized analysis agents',
    status: 'in-progress',
    timestamp: new Date(Date.now() - DEMO_CONSTANTS.TIME_OFFSET_1_MINUTE),
  },
  {
    id: '3',
    title: 'Generating Implementation Guide',
    description: 'Creating structured implementation guide',
    status: 'pending',
  },
]

/**
 * Factory function to create agent activity demo data
 * Wraps Date.now() calls to avoid React purity violations
 */
export const createAgentActivities = (): AgentActivity[] => [
  {
    id: '1',
    agentName: 'Security Auditor',
    action: 'Analyzing authentication patterns...',
    timestamp: new Date(Date.now() - DEMO_CONSTANTS.TIME_OFFSET_5_SECONDS),
  },
  {
    id: '2',
    agentName: 'Tech Comparator',
    action: 'Comparing React Server Components vs traditional SSR',
    timestamp: new Date(Date.now() - DEMO_CONSTANTS.TIME_OFFSET_15_SECONDS),
  },
  {
    id: '3',
    agentName: 'Best Practices',
    action: 'Checking code organization patterns',
    timestamp: new Date(Date.now() - DEMO_CONSTANTS.TIME_OFFSET_25_SECONDS),
  },
  {
    id: '4',
    agentName: 'Implementation Planner',
    action: 'Creating step-by-step implementation guide',
    timestamp: new Date(Date.now() - DEMO_CONSTANTS.TIME_OFFSET_35_SECONDS),
  },
]

/**
 * Factory function to create skill demo data
 * Note: console.log is for demo purposes only
 */
export const createSkills = (): SkillCardProps[] => [
  {
    id: '1',
    title: 'React Server Components',
    description: 'Learn RSC fundamentals and integration with Next.js App Router',
    difficulty: 'intermediate',
    duration: DEMO_CONSTANTS.ACTIVITY_DURATION_MEDIUM,
    tags: ['React', 'Next.js', 'Server Components', 'SSR'],
    status: 'in-progress',
    progress: DEMO_CONSTANTS.SAMPLE_PROGRESS_PERCENTAGE,
    // eslint-disable-next-line no-console -- Demo showcase only
    onSelect: (id) => console.log('Selected skill:', id),
  },
  {
    id: '2',
    title: 'TypeScript Advanced Patterns',
    description: 'Master generics, conditional types, and type inference',
    difficulty: 'advanced',
    duration: DEMO_CONSTANTS.ACTIVITY_DURATION_LONG,
    tags: ['TypeScript', 'Generics', 'Type Safety'],
    status: 'not-started',
    // eslint-disable-next-line no-console -- Demo showcase only
    onSelect: (id) => console.log('Selected skill:', id),
  },
  {
    id: '3',
    title: 'CSS Grid Layout',
    description: 'Build responsive layouts with CSS Grid',
    difficulty: 'beginner',
    duration: DEMO_CONSTANTS.ACTIVITY_DURATION_SHORT,
    tags: ['CSS', 'Layout', 'Responsive'],
    status: 'completed',
    // eslint-disable-next-line no-console -- Demo showcase only
    onSelect: (id) => console.log('Selected skill:', id),
  },
]

/**
 * Factory function to create chat message demo data
 * Wraps Date.now() calls to avoid React purity violations
 */
export const createChatMessages = () => [
  {
    id: 'msg-1',
    role: 'assistant' as const,
    content: 'Hello! How can I help you learn today?',
    timestamp: new Date(Date.now() - DEMO_CONSTANTS.TIME_OFFSET_2_MINUTES),
  },
  {
    id: 'msg-2',
    role: 'user' as const,
    content: 'Can you explain React Server Components?',
    timestamp: new Date(Date.now() - DEMO_CONSTANTS.TIME_OFFSET_1_MINUTE),
  },
  {
    id: 'msg-3',
    role: 'assistant' as const,
    content:
      'Great question! Let me guide you through this. First, think about where traditional React components execute...',
    timestamp: new Date(Date.now() - DEMO_CONSTANTS.TIME_OFFSET_30_SECONDS),
  },
]

/**
 * Available tags for skill filtering
 */
export const availableTags = ['React', 'TypeScript', 'Next.js', 'CSS', 'Node.js', 'GraphQL']

/**
 * Code snippet for CodeBlock demo
 */
export const codeSnippet = `// Server Component (runs on server)
async function ProductList() {
  const products = await db.query('SELECT * FROM products')
  return <div>{products.map(p => <Product key={p.id} {...p} />)}</div>
}`

/**
 * Socratic prompt demo data
 */
export const socraticPromptData = {
  question: 'What challenges arise when React components execute only in the browser?',
  hints: [
    'Consider data fetching requirements',
    'Think about bundle size implications',
    'What about server-only resources?',
  ],
  difficulty: 'medium' as const,
}
