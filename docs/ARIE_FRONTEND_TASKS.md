# 🎨 Arie's Frontend Tasks - SkillForge

**Developer:** Arie (Frontend Specialist)
**Primary Stack:** React 19, TypeScript, Vite, Tailwind CSS, TanStack Query
**Project:** SkillForge - Research-to-Implementation Pipeline

---

## 📋 Table of Contents

1. [Sprint 1: Foundation](#sprint-1-foundation---weeks-1-2)
2. [Sprint 2: Analysis Pipeline UI](#sprint-2-analysis-pipeline-ui---weeks-3-4)
3. [Sprint 3: Artifact Viewer](#sprint-3-artifact-viewer---weeks-5-6)
4. [Sprint 4: Tutoring Interface](#sprint-4-tutoring-interface---weeks-7-8)
5. [Sprint 5: Library & Search](#sprint-5-library--search---weeks-9-10)
6. [Sprint 6: Content Expansion](#sprint-6-content-expansion---week-11)
7. [Sprint 7: Testing & Deployment](#sprint-7-testing--deployment---weeks-12-13)
8. [Quick Reference](#quick-reference)

---

## 🎯 Sprint 1: Foundation - Weeks 1-2

**Sprint Goal:** Setup React 19 frontend with routing, UI components, and mock API integration
**Total Story Points:** 13
**User Stories:** US-1.1 (partial)

---

### ✅ Task 1.3.1: Initialize Vite + React 19 Project [3 pts]

**Status:** Not Started
**Dependencies:** None
**Parallel Work:** Yonatan setting up backend

#### Description
Create a new React 19 project with Vite, TypeScript, and modern tooling.

#### Acceptance Criteria
- [ ] `npm create vite@latest frontend -- --template react-ts` executed successfully
- [ ] React and React-DOM upgraded to v19: `npm install --save-exact react@^19.0.0 react-dom@^19.0.0`
- [ ] `npm run dev` starts development server on http://localhost:5173
- [ ] TypeScript strict mode enabled in `tsconfig.json`
- [ ] Vite proxy configured to forward `/api/*` to `http://localhost:8000`

#### Implementation Steps
```bash
# 1. Create project
cd /Users/ariegoldkin/Arie/projects/chatbot
npm create vite@latest frontend -- --template react-ts

# 2. Install React 19
cd frontend
npm install --save-exact react@^19.0.0 react-dom@^19.0.0

# 3. Update vite.config.ts
```

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

#### Testing
```bash
npm run dev
# Visit http://localhost:5173 - should see React welcome page
```

---

### ✅ Task 1.3.2: Setup Tailwind CSS + Radix UI [2 pts]

**Status:** Not Started
**Dependencies:** Task 1.3.1
**Parallel Work:** Yonatan working on database schema

#### Description
Configure Tailwind CSS for styling and Radix UI for accessible primitives.

#### Acceptance Criteria
- [ ] Tailwind CSS installed and configured
- [ ] `tailwind.config.js` has custom colors and theme
- [ ] Radix UI Dialog, Tabs, Select installed
- [ ] Created `components/ui/` folder with styled primitives
- [ ] Test component renders with Tailwind classes

#### Implementation Steps
```bash
# 1. Install Tailwind
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# 2. Install Radix UI
npm install @radix-ui/react-dialog @radix-ui/react-tabs @radix-ui/react-select

# 3. Install utilities
npm install clsx tailwind-merge lucide-react
```

```typescript
// tailwind.config.js
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          500: '#3b82f6',
          600: '#2563eb',
        },
      },
    },
  },
  plugins: [],
}
```

```css
/* src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

#### File Structure
```
src/
  components/
    ui/
      button.tsx
      dialog.tsx
      input.tsx
```

---

### ✅ Task 1.3.3: Configure React Router [2 pts]

**Status:** Not Started
**Dependencies:** Task 1.3.2
**Parallel Work:** Yonatan working on Docker setup

#### Description
Setup routing with React Router v7 for navigation between pages.

#### Acceptance Criteria
- [ ] React Router installed (`react-router-dom@^7.9.4`)
- [ ] Routes defined: `/`, `/analyze/:id`, `/tutor/:sessionId`, `/library`
- [ ] Layout component with navigation bar
- [ ] Active route highlighted in navigation
- [ ] 404 page for unknown routes

#### Implementation Steps
```bash
npm install react-router-dom@^7.9.4
```

```typescript
// src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Analyze from './pages/Analyze'
import Tutor from './pages/Tutor'
import Library from './pages/Library'
import NotFound from './pages/NotFound'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="analyze/:id" element={<Analyze />} />
          <Route path="tutor/:sessionId" element={<Tutor />} />
          <Route path="library" element={<Library />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
```

---

### ✅ Task 1.3.4: Setup State Management (TanStack Query + Zustand) [3 pts]

**Status:** Not Started
**Dependencies:** Task 1.3.3
**Parallel Work:** Yonatan completing Sprint 1 backend tasks

#### Description
Configure TanStack Query for server state and Zustand for client state.

#### Acceptance Criteria
- [ ] TanStack Query installed with QueryClient provider
- [ ] Zustand store created for global UI state (theme, modals)
- [ ] React Query DevTools enabled in development
- [ ] Example query hook created (e.g., `useAnalysis`)

#### Implementation Steps
```bash
npm install @tanstack/react-query@^5.62.7 zustand@^5.0.2
npm install -D @tanstack/react-query-devtools
```

```typescript
// src/main.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
})

root.render(
  <QueryClientProvider client={queryClient}>
    <App />
    <ReactQueryDevtools initialIsOpen={false} />
  </QueryClientProvider>
)
```

```typescript
// src/stores/uiStore.ts
import { create } from 'zustand'

interface UIState {
  theme: 'light' | 'dark'
  toggleTheme: () => void
}

export const useUIStore = create<UIState>((set) => ({
  theme: 'light',
  toggleTheme: () => set((state) => ({
    theme: state.theme === 'light' ? 'dark' : 'light'
  })),
}))
```

---

### ✅ Task 1.3.5: Create Page Shells & Basic Components [3 pts]

**Status:** Not Started
**Dependencies:** Task 1.3.4
**Integration Point:** API contract meeting with Yonatan (Day 3)

#### Description
Build empty page components and reusable UI primitives.

#### Acceptance Criteria
- [ ] `Home.tsx` - Landing page with module cards (Analyze, Tutor, Library)
- [ ] `Analyze.tsx` - URL input form (non-functional yet)
- [ ] `Library.tsx` - Empty state placeholder
- [ ] `Tutor.tsx` - Chat interface skeleton
- [ ] `components/ui/Button.tsx` - Reusable button component
- [ ] `components/ui/Input.tsx` - Reusable input component

#### File Structure
```
src/
  pages/
    Home.tsx
    Analyze.tsx
    Tutor.tsx
    Library.tsx
    NotFound.tsx
  components/
    Layout.tsx
    ui/
      Button.tsx
      Input.tsx
      Card.tsx
```

#### Example Component
```typescript
// src/shared/components/ui/Button.tsx
import { ButtonHTMLAttributes } from 'react'
import { clsx } from 'clsx'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
}

export function Button({
  variant = 'primary',
  size = 'md',
  className,
  ...props
}: ButtonProps) {
  return (
    <button
      className={clsx(
        'rounded-lg font-medium transition-colors',
        {
          'bg-primary-600 text-white hover:bg-primary-700': variant === 'primary',
          'bg-gray-200 text-gray-900 hover:bg-gray-300': variant === 'secondary',
          'text-sm px-3 py-1.5': size === 'sm',
          'text-base px-4 py-2': size === 'md',
        },
        className
      )}
      {...props}
    />
  )
}
```

---

### 🔗 Integration Point: API Contract Meeting (Day 3)

**Participants:** Arie + Yonatan
**Duration:** 1 hour
**Goal:** Define API schemas for `/api/v1/analyze` endpoint

#### Agenda
1. **Review OpenAPI spec** (Yonatan presents)
2. **Agree on request/response formats**
3. **Define error codes**
4. **Lock contract** (no changes without discussion)

#### Expected Outputs
- [ ] Documented API contract in `docs/API_CONTRACT.md`
- [ ] TypeScript types generated in `frontend/src/types/api.ts`
- [ ] Arie can proceed with mock API responses

---

## 🔄 Sprint 2: Analysis Pipeline UI - Weeks 3-4

**Sprint Goal:** Build real-time progress UI with SSE connection to backend
**Total Story Points:** 13
**User Stories:** US-1.2

---

### ✅ Task 2.1: Create SSE Client Hook [5 pts]

**Status:** ✅ COMPLETE (November 25, 2025)
**Dependencies:** Sprint 1 complete, SSE schema from Yonatan (Day 1)
**Documentation:** [Issue #43 Validation](./issues/043-sse-client-hook/ISSUE_43_VALIDATION_COMPLETE.md)

#### Description
Build a reusable React hook for consuming Server-Sent Events from backend.

#### Acceptance Criteria
- [x] `useSSE(url)` hook connects to SSE endpoint
- [x] Hook returns `{ events, error, isConnected, isComplete, latestEvent }` state
- [x] Automatically reconnects on connection loss
- [x] Cleans up EventSource on unmount
- [x] TypeScript types for all event types
- [x] Error handling for connection failures

#### Implementation
```typescript
// src/hooks/useSSE.ts
import { useEffect, useState } from 'react'

interface SSEEvent {
  stage: string
  status: 'pending' | 'running' | 'complete' | 'failed'
  details?: Record<string, any>
  timestamp: string
}

interface UseSSEResult {
  events: SSEEvent[]
  error: Error | null
  isConnected: boolean
}

export function useSSE(url: string): UseSSEResult {
  const [events, setEvents] = useState<SSEEvent[]>([])
  const [error, setError] = useState<Error | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    const eventSource = new EventSource(url)

    eventSource.onopen = () => {
      setIsConnected(true)
      setError(null)
    }

    eventSource.addEventListener('progress', (e) => {
      const event: SSEEvent = JSON.parse(e.data)
      setEvents((prev) => [...prev, event])
    })

    eventSource.addEventListener('complete', (e) => {
      const event: SSEEvent = JSON.parse(e.data)
      setEvents((prev) => [...prev, event])
      eventSource.close()
      setIsConnected(false)
    })

    eventSource.onerror = () => {
      setError(new Error('SSE connection failed'))
      setIsConnected(false)
      eventSource.close()
    }

    return () => {
      eventSource.close()
    }
  }, [url])

  return { events, error, isConnected }
}
```

#### Testing Checklist
- [x] Test with mock SSE server (can use Express locally)
- [x] Test reconnection on network loss
- [x] Test cleanup on component unmount
- [x] Test multiple simultaneous SSE connections

#### Test Results (16/16 passing)
- `sseStore.test.ts` - 6 tests (store state management)
- `useSSE.test.tsx` - 3 tests (hook behavior)
- `useAnalysis.test.tsx` - 3 tests (analysis data fetching)
- Plus 4 setup verification tests

---

### ✅ Task 2.2: Build ProgressTracker Component [5 pts]

**Status:** Not Started
**Dependencies:** Task 2.1
**Parallel Work:** Yonatan implementing supervisor pattern

#### Description
Create a visual component showing analysis progress through multiple stages.

#### Acceptance Criteria
- [ ] Displays current stage with visual indicator (spinner/checkmark)
- [ ] Shows list of all stages (extraction, supervisor, agents, aggregation, artifact)
- [ ] Completed stages show checkmark, current shows spinner, pending shows gray
- [ ] Shows which sub-agents are running (if applicable)
- [ ] Responsive design (works on mobile)
- [ ] Smooth animations between stage transitions

#### Component Design
```typescript
// src/shared/components/ProgressTracker.tsx
import { useSSE } from '../hooks/useSSE'
import { CheckCircle, Loader, Circle } from 'lucide-react'

interface ProgressTrackerProps {
  analysisId: string
}

const STAGES = [
  { id: 'extraction', label: 'Extracting Content' },
  { id: 'supervisor_routing', label: 'Analyzing Content Type' },
  { id: 'tech_comparison', label: 'Comparing Technologies' },
  { id: 'integration_feasibility', label: 'Checking Integration' },
  { id: 'security_audit', label: 'Security Analysis' },
  { id: 'performance_analysis', label: 'Performance Review' },
  { id: 'aggregation', label: 'Synthesizing Findings' },
  { id: 'artifact_generation', label: 'Generating Artifact' },
]

export function ProgressTracker({ analysisId }: ProgressTrackerProps) {
  const { events, error, isConnected } = useSSE(
    `/api/v1/analyze/${analysisId}/stream`
  )

  const getStageStatus = (stageId: string) => {
    const event = events.find(e => e.stage === stageId)
    return event?.status || 'pending'
  }

  if (error) {
    return <div className="text-red-600">Connection error: {error.message}</div>
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        {isConnected ? (
          <Loader className="w-4 h-4 animate-spin text-primary-600" />
        ) : (
          <Circle className="w-4 h-4 text-gray-400" />
        )}
        <span className="text-sm text-gray-600">
          {isConnected ? 'Analyzing...' : 'Disconnected'}
        </span>
      </div>

      <div className="space-y-2">
        {STAGES.map((stage) => {
          const status = getStageStatus(stage.id)
          return (
            <div key={stage.id} className="flex items-center gap-3">
              {status === 'complete' && (
                <CheckCircle className="w-5 h-5 text-green-600" />
              )}
              {status === 'running' && (
                <Loader className="w-5 h-5 animate-spin text-primary-600" />
              )}
              {status === 'pending' && (
                <Circle className="w-5 h-5 text-gray-300" />
              )}
              {status === 'failed' && (
                <XCircle className="w-5 h-5 text-red-600" />
              )}
              <span className={clsx(
                'text-sm',
                status === 'complete' && 'text-green-700',
                status === 'running' && 'text-primary-700 font-medium',
                status === 'pending' && 'text-gray-400',
                status === 'failed' && 'text-red-700'
              )}>
                {stage.label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

---

### ✅ Task 2.3: Build Analysis View Page [3 pts]

**Status:** Not Started
**Dependencies:** Task 2.2
**Parallel Work:** Yonatan implementing first 3 sub-agents

#### Description
Create the main analysis page that shows progress and results.

#### Acceptance Criteria
- [ ] Route `/analyze/:id` renders correctly
- [ ] Shows URL being analyzed
- [ ] Displays `ProgressTracker` component
- [ ] Shows "Cancel" button (functionality in later sprint)
- [ ] When complete, shows "Download Artifact" button
- [ ] Loading skeleton while fetching initial analysis data

#### File Structure
```typescript
// src/pages/Analyze.tsx
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ProgressTracker } from '../components/ProgressTracker'
import { Button } from '../components/ui/Button'

export function Analyze() {
  const { id } = useParams()

  const { data: analysis, isLoading } = useQuery({
    queryKey: ['analysis', id],
    queryFn: () => fetch(`/api/v1/analyze/${id}`).then(r => r.json()),
  })

  if (isLoading) return <AnalysisSkeleton />

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">Analyzing Content</h1>
        <p className="text-gray-600">{analysis.url}</p>
      </div>

      <ProgressTracker analysisId={id!} />

      {analysis.status === 'complete' && (
        <div className="mt-6 flex gap-3">
          <Button onClick={() => downloadArtifact(id!)}>
            Download Artifact
          </Button>
          <Button variant="secondary">
            Preview
          </Button>
        </div>
      )}
    </div>
  )
}
```

---

### 🔗 Integration Point: Test SSE with Live Backend (Day 8)

**Participants:** Arie + Yonatan
**Duration:** 30 minutes
**Goal:** Verify SSE events flow correctly from backend to frontend

#### Testing Checklist
- [ ] Start backend server
- [ ] Submit analysis from frontend
- [ ] Verify SSE connection establishes
- [ ] Verify all stage events appear in UI
- [ ] Test error handling (kill backend mid-analysis)
- [ ] Verify completion event closes connection

---

## 🎨 Sprint 3: Artifact Viewer - Weeks 5-6

**Sprint Goal:** Display generated artifacts with markdown preview and download
**Total Story Points:** 13
**User Stories:** US-1.3, US-1.4, US-1.5

---

### ✅ Task 3.1: Install Markdown Rendering Dependencies [1 pt]

**Status:** ✅ COMPLETE (November 29, 2024)
**Dependencies:** Sprint 2 complete
**PR:** [#148](https://github.com/ArieGoldkin/SkillForge/pull/148)
**Documentation:** [Issue #60 Docs](./issues/060-markdown-dependencies/README.md)

#### Installed Packages
- `react-markdown@9.1.0` - Markdown rendering
- `remark-gfm@4.0.1` - GitHub Flavored Markdown
- `prismjs@1.30.0` + `@types/prismjs@1.26.5` - Syntax highlighting
- Added `prism-tomorrow.css` theme import in `main.tsx`

#### Verification
- ✅ Build passes
- ✅ 122/122 tests passing
- ✅ 0 vulnerabilities

---

### ✅ Task 3.2: Create MarkdownPreview Component [5 pts]

**Status:** Not Started
**Dependencies:** Task 3.1, Artifact schema from Yonatan (Day 2)

#### Description
Build a component that renders markdown with syntax highlighting.

#### Acceptance Criteria
- [ ] Renders markdown from string prop
- [ ] Syntax highlighting for code blocks (Python, TypeScript, Bash)
- [ ] Responsive design (works on mobile)
- [ ] Proper styling for headings, lists, tables, blockquotes
- [ ] Copy button on code blocks
- [ ] Renders GitHub Flavored Markdown (tables, task lists)

#### Implementation
```typescript
// src/shared/components/MarkdownPreview.tsx
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import Prism from 'prismjs'
import 'prismjs/themes/prism-tomorrow.css'
import 'prismjs/components/prism-python'
import 'prismjs/components/prism-typescript'
import 'prismjs/components/prism-bash'

interface MarkdownPreviewProps {
  content: string
}

export function MarkdownPreview({ content }: MarkdownPreviewProps) {
  useEffect(() => {
    Prism.highlightAll()
  }, [content])

  return (
    <div className="prose prose-lg max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '')
            return !inline && match ? (
              <div className="relative">
                <button
                  onClick={() => copyToClipboard(String(children))}
                  className="absolute top-2 right-2 text-xs px-2 py-1 bg-gray-700 text-white rounded"
                >
                  Copy
                </button>
                <pre className={className}>
                  <code {...props}>{children}</code>
                </pre>
              </div>
            ) : (
              <code className="bg-gray-100 px-1 py-0.5 rounded" {...props}>
                {children}
              </code>
            )
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
```

---

### ✅ Task 3.3: Create Artifact Download Handler [2 pts]

**Status:** Not Started
**Dependencies:** Task 3.2

#### Description
Implement download functionality for markdown artifacts.

#### Acceptance Criteria
- [ ] Clicking "Download" button downloads .md file
- [ ] Filename is descriptive (from analysis title)
- [ ] File downloads correctly on all browsers
- [ ] Shows success toast after download

#### Implementation
```typescript
// src/utils/download.ts
export async function downloadArtifact(artifactId: string) {
  const response = await fetch(`/api/v1/artifacts/${artifactId}/download`)
  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = response.headers.get('Content-Disposition')?.split('filename=')[1] || 'artifact.md'
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}
```

---

### ✅ Task 3.4: Build Preview Modal [3 pts]

**Status:** Not Started
**Dependencies:** Task 3.3

#### Description
Create a modal that shows markdown preview before downloading.

#### Acceptance Criteria
- [ ] Modal opens when clicking "Preview" button
- [ ] Shows full markdown rendered with `MarkdownPreview` component
- [ ] Modal is scrollable for long content
- [ ] "Download" and "Close" buttons in modal footer
- [ ] Keyboard shortcut to close (Escape key)
- [ ] Accessible (focus trap, ARIA labels)

#### Implementation
```typescript
// src/shared/components/ArtifactPreviewModal.tsx
import * as Dialog from '@radix-ui/react-dialog'
import { MarkdownPreview } from './MarkdownPreview'
import { Button } from './ui/Button'

interface ArtifactPreviewModalProps {
  artifactId: string
  isOpen: boolean
  onClose: () => void
}

export function ArtifactPreviewModal({
  artifactId,
  isOpen,
  onClose
}: ArtifactPreviewModalProps) {
  const { data: artifact } = useQuery({
    queryKey: ['artifact', artifactId],
    queryFn: () => fetch(`/api/v1/artifacts/${artifactId}`).then(r => r.json()),
    enabled: isOpen,
  })

  return (
    <Dialog.Root open={isOpen} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-auto p-6">
          <Dialog.Title className="text-2xl font-bold mb-4">
            Artifact Preview
          </Dialog.Title>

          {artifact && (
            <MarkdownPreview content={artifact.markdown_content} />
          )}

          <div className="mt-6 flex gap-3 justify-end">
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
            <Button onClick={() => downloadArtifact(artifactId)}>
              Download
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
```

---

### ✅ Task 3.5: Add Copy-to-Clipboard for Prompts [2 pts]

**Status:** Not Started
**Dependencies:** Task 3.4

#### Description
Add one-click copy for "Claude Code Prompt" sections.

#### Acceptance Criteria
- [ ] Copy button appears next to prompt sections
- [ ] Clicking copies text to clipboard
- [ ] Success toast appears: "Copied to clipboard!"
- [ ] Works on all modern browsers
- [ ] Fallback for older browsers (document.execCommand)

#### Implementation
```typescript
// src/hooks/useClipboard.ts
import { useState } from 'react'

export function useClipboard() {
  const [copied, setCopied] = useState(false)

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      // Fallback for older browsers
      const textArea = document.createElement('textarea')
      textArea.value = text
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return { copy, copied }
}
```

---

## 🎓 Sprint 4: Tutoring Interface - Weeks 7-8

**Sprint Goal:** Build interactive chat interface for Socratic tutoring
**Total Story Points:** 13
**User Stories:** US-2.1, US-2.2, US-2.3, US-2.4

---

### ✅ Task 4.1: Create TutorChat Component [5 pts]

**Status:** Not Started
**Dependencies:** Sprint 3 complete

#### Description
Build a chat interface for tutoring sessions.

#### Acceptance Criteria
- [ ] Message list with auto-scroll to bottom
- [ ] User messages aligned right, assistant left
- [ ] Avatar icons for user and AI tutor
- [ ] Markdown rendering in assistant messages
- [ ] Typing indicator when assistant is responding
- [ ] Input field with "Send" button
- [ ] Keyboard shortcut (Enter to send, Shift+Enter for new line)

#### Component Structure
```typescript
// src/shared/components/TutorChat.tsx
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export function TutorChat({ sessionId }: { sessionId: string }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)

  const sendMessage = useMutation({
    mutationFn: (content: string) =>
      fetch(`/api/v1/tutor/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      }).then(r => r.json()),
    onSuccess: (data) => {
      setMessages(prev => [...prev, data])
      setIsTyping(false)
    },
  })

  const handleSend = () => {
    if (!input.trim()) return
    const userMessage = { id: Date.now().toString(), role: 'user', content: input, timestamp: new Date().toISOString() }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsTyping(true)
    sendMessage.mutate(input)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map(msg => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        {isTyping && <TypingIndicator />}
      </div>

      <div className="border-t p-4">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            placeholder="Type your message..."
            className="flex-1 resize-none rounded-lg border p-2"
            rows={2}
          />
          <Button onClick={handleSend} disabled={!input.trim()}>
            Send
          </Button>
        </div>
      </div>
    </div>
  )
}
```

---

### ✅ Task 4.2: Create Topic Selection Modal [3 pts]

**Status:** Not Started
**Dependencies:** Task 4.1

#### Description
Modal for selecting which topic to learn when starting tutoring.

#### Acceptance Criteria
- [ ] Shows list of topics extracted from analysis
- [ ] User can select one topic
- [ ] "Start Learning" button creates tutoring session
- [ ] Option to learn "All Topics" (tutor chooses)
- [ ] Modal opens from "Teach Me" button on artifact view

---

### ✅ Task 4.3: Implement Session Resume Logic [3 pts]

**Status:** Not Started
**Dependencies:** Task 4.2

#### Description
Allow users to resume previous tutoring sessions.

#### Acceptance Criteria
- [ ] Store active session ID in localStorage
- [ ] Show "Resume Session" button if active session exists
- [ ] Load conversation history when resuming
- [ ] Clear localStorage when session completed
- [ ] Handle case where session no longer exists on server

---

### ✅ Task 4.4: Add Exit Tutoring Functionality [2 pts]

**Status:** Not Started
**Dependencies:** Task 4.3

#### Description
Allow users to explicitly exit tutoring sessions.

#### Acceptance Criteria
- [ ] "Exit Tutoring" button in chat header
- [ ] Confirmation dialog: "Are you sure?"
- [ ] Marks session as completed on backend
- [ ] Redirects to analysis view
- [ ] Clears localStorage

---

## 📚 Sprint 5: Library & Search - Weeks 9-10

**Sprint Goal:** Build searchable library of past analyses
**Total Story Points:** 13
**User Stories:** US-3.1, US-3.2, US-3.3, US-3.4

---

### ✅ Task 5.1: Create Library Page [5 pts]

**Status:** Not Started
**Dependencies:** Sprint 4 complete

#### Description
Build main library page with analysis cards.

#### Acceptance Criteria
- [ ] Grid layout of analysis cards (responsive)
- [ ] Each card shows: title, URL, date, topics, download button
- [ ] Pagination (20 per page)
- [ ] Empty state for new users
- [ ] Loading skeletons while fetching
- [ ] Click card to view details

---

### ✅ Task 5.2: Implement Search with Debounce [3 pts]

**Status:** Not Started
**Dependencies:** Task 5.1

#### Description
Add search input that queries backend.

#### Acceptance Criteria
- [ ] Search input at top of library
- [ ] Debounced (500ms) to avoid excessive requests
- [ ] Updates URL params (?search=query)
- [ ] Highlights matching terms in results
- [ ] "No results" message with suggestions

---

### ✅ Task 5.3: Build Filter UI [3 pts]

**Status:** Not Started
**Dependencies:** Task 5.2

#### Description
Add filter dropdowns for content type and topics.

#### Acceptance Criteria
- [ ] Content type dropdown (All, Article, Video, Repo)
- [ ] Topics multi-select (Radix Select)
- [ ] Active filters shown as removable chips
- [ ] "Clear Filters" button
- [ ] Filters update URL params

---

### ✅ Task 5.4: Add Sort Selector [2 pts]

**Status:** Not Started
**Dependencies:** Task 5.3

#### Description
Allow sorting by date or popularity.

#### Acceptance Criteria
- [ ] Sort dropdown (Recent, Popular)
- [ ] Updates URL params (?sort=recent)
- [ ] Default is "Recent"
- [ ] Results reorder immediately

---

## 🌐 Sprint 6: Content Expansion - Week 11

**Sprint Goal:** Update UI for YouTube and GitHub content types
**Total Story Points:** 8
**User Stories:** US-4.1, US-4.2 (UI only)

---

### ✅ Task 6.1: Add Content Type Indicators [3 pts]

**Status:** Not Started
**Dependencies:** Sprint 5 complete

#### Description
Show icons/badges for different content types.

#### Acceptance Criteria
- [ ] Article icon (📄), Video icon (🎥), Repo icon (💻)
- [ ] Content type badge on analysis cards
- [ ] Different colors per type
- [ ] Shows in artifact viewer

---

### ✅ Task 6.2: Update Artifact Template for Videos [3 pts]

**Status:** Not Started
**Dependencies:** Task 6.1, Yonatan's video extractor

#### Description
Handle video-specific metadata in UI.

#### Acceptance Criteria
- [ ] Shows video duration
- [ ] Displays timestamps in key findings
- [ ] YouTube thumbnail in preview
- [ ] Link to original video

---

### ✅ Task 6.3: Update Artifact Template for Repos [2 pts]

**Status:** Not Started
**Dependencies:** Task 6.2, Yonatan's GitHub extractor

#### Description
Handle repo-specific metadata in UI.

#### Acceptance Criteria
- [ ] Shows repo language/stars
- [ ] File structure visualization
- [ ] Link to original repo
- [ ] README preview

---

## 🚀 Sprint 7: Testing & Deployment - Weeks 12-13

**Sprint Goal:** E2E tests, production deployment, polish
**Total Story Points:** 21
**User Stories:** All (testing)

---

### ✅ Task 7.1: Write E2E Tests with Playwright [8 pts]

**Status:** Not Started
**Dependencies:** All features complete

#### Test Cases
- [ ] Submit URL and view progress
- [ ] Download artifact
- [ ] Preview markdown
- [ ] Start tutoring session
- [ ] Search library
- [ ] Filter by content type
- [ ] Analyze YouTube video
- [ ] Analyze GitHub repo
- [ ] Error handling (invalid URL)
- [ ] Responsive design (mobile)

---

### ✅ Task 7.2: Performance Optimization [5 pts]

**Status:** Not Started
**Dependencies:** Task 7.1

#### Tasks
- [ ] Code splitting (React.lazy for routes)
- [ ] Image lazy loading
- [ ] Virtualized lists for library (react-window)
- [ ] Bundle size analysis (vite-bundle-visualizer)
- [ ] Lighthouse audit (score >90)

---

### ✅ Task 7.3: Deploy to Vercel [3 pts]

**Status:** Not Started
**Dependencies:** Task 7.2

#### Steps
- [ ] Create Vercel project
- [ ] Configure environment variables
- [ ] Setup custom domain (optional)
- [ ] Enable preview deployments
- [ ] Test production build

---

### ✅ Task 7.4: UI Polish [5 pts]

**Status:** Not Started
**Dependencies:** Task 7.3

#### Tasks
- [ ] Add error boundaries
- [ ] Toast notifications (success/error)
- [ ] Loading states everywhere
- [ ] Smooth transitions/animations
- [ ] Accessibility audit (ARIA labels, keyboard nav)

---

## 🎯 Quick Reference

### Daily Workflow

**Morning (15 min):**
1. Pull latest from backend (if Yonatan pushed changes)
2. Check for updated API contracts in docs/
3. Review blockers in shared doc

**During Day:**
- Push commits frequently (small, atomic changes)
- Update task status in this doc
- Flag blockers in Slack/Discord immediately

**End of Day (10 min):**
1. Push all work in progress
2. Update task statuses
3. Note any blockers for tomorrow

---

### Tech Stack Quick Reference

**Core:**
- React 19.0.0
- TypeScript 5.7.2
- Vite 6.0.3
- Tailwind CSS 3.4.15

**State:**
- TanStack Query 5.62.7 (server state)
- Zustand 5.0.2 (client state)

**UI:**
- Radix UI (Dialog, Tabs, Select)
- Lucide React (icons)
- react-markdown + Prism.js

**Testing:**
- Vitest (unit tests)
- Playwright (E2E tests)
- React Testing Library

---

### Useful Commands

```bash
# Development
npm run dev              # Start dev server
npm run build            # Production build
npm run preview          # Preview production build

# Testing
npm run test             # Run unit tests
npm run test:e2e         # Run E2E tests
npm run test:watch       # Watch mode

# Linting
npm run lint             # ESLint
npm run format           # Prettier

# Type Checking
npm run type-check       # TypeScript check
```

---

### When Blocked

**If blocked by backend (>4 hours):**
1. Create mock API responses
2. Continue with UI development
3. Flag blocker in daily standup

**If blocked by unclear requirements:**
1. Check user stories in `USER_STORIES.md`
2. Ask Yonatan or PM for clarification
3. Document decision in task notes

---

**Document Maintained By:** Arie
**Last Updated:** November 29, 2024
**Review:** Update task statuses daily
