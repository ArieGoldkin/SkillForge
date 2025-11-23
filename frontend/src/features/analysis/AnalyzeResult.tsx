import { useParams } from '@tanstack/react-router'

export default function AnalyzeResult() {
  // TanStack Router provides type-safe params automatically
  const { id } = useParams({ from: '/analyze/$id' })

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Analysis Result</h1>
      <p className="text-muted-foreground mb-4">Analysis ID: {id}</p>
      <div className="space-y-4">
        <div className="p-6 border rounded-lg">
          <h2 className="text-xl font-semibold mb-2">Agent Findings</h2>
          <p className="text-muted-foreground">Multi-agent analysis results will appear here</p>
        </div>
      </div>
    </div>
  )
}
