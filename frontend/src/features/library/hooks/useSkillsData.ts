import { useNavigate } from '@tanstack/react-router'

interface Analysis {
  id: string
  title: string | null
  content_type: string
  status: string
}

export function useSkillsData(analyses: Analysis[] | undefined) {
  const navigate = useNavigate()

  return (analyses || []).map((analysis) => ({
    id: analysis.id,
    title: analysis.title || 'Untitled',
    description: `Analysis of ${analysis.content_type}`,
    thumbnail: `https://api.dicebear.com/7.x/shapes/svg?seed=${analysis.id}`,
    duration: 25,
    difficulty: 'intermediate' as const,
    tags: [analysis.content_type, analysis.status],
    progress: analysis.status === 'complete' ? 100 : 65,
    status:
      analysis.status === 'complete'
        ? ('completed' as const)
        : analysis.status === 'failed' ||
            analysis.status === 'extraction_failed' ||
            analysis.status === 'analysis_failed' ||
            analysis.status === 'artifact_failed' ||
            analysis.status === 'quality_gate_failed'
          ? ('failed' as const)
          : ('in-progress' as const),
    onSelect: (id: string) => {
      navigate({ to: '/analyze/$id', params: { id } })
    },
  }))
}
