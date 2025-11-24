# Feature Components

Production-ready React components for the SkillForge application, organized by feature domain.

## Quick Start

```tsx
import {
  AnalysisProgressCard,
  AnalysisStepList,
  AgentActivityFeed,
} from '@/shared/components/features/analysis'

import {
  SkillCard,
  SkillFilters,
  SkillSearch,
  SkillGridView,
} from '@/shared/components/features/library'

import {
  ChatMessage,
  ChatInput,
  CodeBlock,
  SocraticPrompt,
} from '@/shared/components/features/tutor'
```

## Analysis Components

### AnalysisProgressCard

Display overall analysis progress with stage indicator.

```tsx
<AnalysisProgressCard
  stage="analyzing"
  progress={60}
  currentStep="Multi-Agent Analysis"
  totalSteps={3}
  completedSteps={2}
  estimatedTimeRemaining="2-3 minutes"
/>
```

### AnalysisStepList

Timeline view of analysis steps with status indicators.

```tsx
<AnalysisStepList
  steps={[
    {
      id: '1',
      title: 'Extracting Content',
      description: 'Fetching and parsing content from URL',
      status: 'completed',
      timestamp: new Date(Date.now() - 120000),
      duration: 5000,
    },
    {
      id: '2',
      title: 'Multi-Agent Analysis',
      description: 'Running specialized analysis agents',
      status: 'in-progress',
      timestamp: new Date(),
    },
  ]}
/>
```

### AgentActivityFeed

Real-time activity log from LangGraph agents.

```tsx
<AgentActivityFeed
  activities={[
    {
      id: '1',
      agentName: 'Security Auditor',
      action: 'Analyzing authentication patterns...',
      timestamp: new Date(),
    },
  ]}
  isLive={true}
  maxItems={10}
/>
```

## Library Components

### SkillCard

Individual skill resource card with metadata and progress.

```tsx
<SkillCard
  id="react-rsc"
  title="React Server Components"
  description="Learn RSC fundamentals and integration with Next.js"
  difficulty="intermediate"
  duration={45}
  tags={['React', 'Next.js', 'Server Components']}
  status="in-progress"
  progress={60}
  onSelect={(id) => router.push(`/skills/${id}`)}
/>
```

### SkillFilters

Filter sidebar with difficulty, status, and tag options.

```tsx
const [filters, setFilters] = useState<SkillFiltersType>({
  difficulty: [],
  status: [],
  tags: [],
  durationRange: [0, 1000],
})

<SkillFilters
  filters={filters}
  onChange={setFilters}
  availableTags={['React', 'TypeScript', 'Next.js']}
/>
```

### SkillSearch

Debounced search input with loading indicator.

```tsx
<SkillSearch
  placeholder="Search skills..."
  onSearch={(query) => fetchSkills(query)}
  debounceMs={300}
/>
```

### SkillGridView

Responsive grid layout for skill cards with loading and empty states.

```tsx
<SkillGridView
  skills={skillsData}
  onSelectSkill={(id) => router.push(`/skills/${id}`)}
  loading={isLoading}
  emptyMessage="Try adjusting your filters or search query"
/>
```

## Tutor Components

### ChatMessage

Message bubble for user/assistant chat with streaming support.

```tsx
<ChatMessage
  role="assistant"
  content="Hello! How can I help you today?"
  timestamp={new Date()}
  isStreaming={false}
/>

<ChatMessage
  role="user"
  content="I need help with React Server Components"
  timestamp={new Date()}
/>
```

### ChatInput

Auto-growing textarea with send button and character counter.

```tsx
<ChatInput
  onSend={(message) => sendMessage(message)}
  disabled={isSending}
  placeholder="Type your message..."
  maxLength={2000}
/>
```

### CodeBlock

Syntax-highlighted code snippets with copy functionality.

```tsx
<CodeBlock
  code={`const greeting = "Hello, world!";\nconsole.log(greeting);`}
  language="javascript"
  filename="example.js"
  showLineNumbers={true}
/>
```

### SocraticPrompt

Formatted Socratic question with expandable hints.

```tsx
<SocraticPrompt
  question="What challenges arise when React components execute only in the browser?"
  hints={[
    'Consider data fetching requirements',
    'Think about bundle size implications',
    'What about server-only resources?',
  ]}
  difficulty="medium"
/>
```

## Theme Support

All components support light/dark mode automatically via CSS variables. Toggle theme using the `ThemeToggle` component in the navigation.

## Accessibility

All components follow WCAG 2.1 AA guidelines:

- Keyboard navigation (Tab, Enter, Space)
- ARIA labels for screen readers
- Semantic HTML
- Focus indicators
- Color contrast compliant

## Responsive Design

Components are mobile-first and responsive:

- Mobile: < 768px (default)
- Tablet: `md:` (>= 768px)
- Desktop: `lg:` (>= 1024px)

## Visual Testing

Use the `FeaturesShowcase` component to test all components:

```tsx
import { FeaturesShowcase } from '@/shared/components/features/FeaturesShowcase'

// In your route
<FeaturesShowcase />
```

## TypeScript

All components are fully typed with exported interfaces:

```tsx
import type {
  AnalysisStep,
  AnalysisStepStatus,
  AgentActivity,
  SkillCardProps,
  SkillDifficulty,
  SkillStatus,
  SkillFiltersType,
  MessageRole,
  SocraticDifficulty,
} from '@/components/features/*'
```

## Performance

- Bundle size: 122KB gzipped
- Debounced search (300ms default)
- Lazy image loading
- Optimized re-renders

## Next Steps

1. **Page Integration:** Use components in Analysis, Library, and Tutor pages
2. **State Management:** Connect to Zustand stores or TanStack Query
3. **API Integration:** Connect to FastAPI backend endpoints
4. **Enhancements:**
   - Add react-markdown for ChatMessage
   - Add react-syntax-highlighter for CodeBlock
   - Add virtual scrolling for long lists (optional)

## Documentation

See `frontend/PHASE_3_COMPONENTS.md` for comprehensive implementation details.
