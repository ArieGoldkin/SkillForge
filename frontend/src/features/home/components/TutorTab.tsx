/**
 * TutorTab - Showcase for tutor feature components
 *
 * Demonstrates:
 * - ChatMessage
 * - SocraticPrompt
 * - CodeBlock
 * - ChatInput
 */

import * as React from 'react'

import { ChatInput } from '@features/tutor/components/ChatInput'
import { ChatMessage } from '@features/tutor/components/ChatMessage'
import { CodeBlock } from '@features/tutor/components/CodeBlock'
import { SocraticPrompt } from '@features/tutor/components/SocraticPrompt'

import { codeSnippet, createChatMessages, socraticPromptData } from './showcase-data'
import { ShowcaseSection } from './ShowcaseSection'

/**
 * TutorTab component
 */
export const TutorTab: React.FC = () => {
  // Use useState initializer to ensure Date.now() is called only once (React purity)
  const [messages] = React.useState(createChatMessages)

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold mb-4">Tutor Components</h2>

      <div className="space-y-6">
        <ShowcaseSection title="ChatMessage">
          <div className="bg-card border rounded-lg p-6 space-y-4">
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                role={msg.role}
                content={msg.content}
                timestamp={msg.timestamp}
              />
            ))}
          </div>
        </ShowcaseSection>

        <ShowcaseSection title="SocraticPrompt">
          <SocraticPrompt
            question={socraticPromptData.question}
            hints={socraticPromptData.hints}
            difficulty={socraticPromptData.difficulty}
          />
        </ShowcaseSection>

        <ShowcaseSection title="CodeBlock">
          <CodeBlock
            code={codeSnippet}
            language="typescript"
            filename="ProductList.tsx"
            showLineNumbers={true}
          />
        </ShowcaseSection>

        <ShowcaseSection title="ChatInput">
          <ChatInput
            onSend={(message) => console.log('Sent:', message)} // eslint-disable-line no-console -- Demo showcase only
            placeholder="Type your message..."
          />
        </ShowcaseSection>
      </div>
    </div>
  )
}

TutorTab.displayName = 'TutorTab'
