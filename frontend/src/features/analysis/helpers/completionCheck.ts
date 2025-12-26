/**
 * Check if analysis is truly complete (all stages passed, 100% progress)
 */
export const checkIsTrulyComplete = (params: {
  hasFailedStages: boolean
  completed?: boolean
  urlArtifactId?: string
  resolvedStatus?: string
  isComplete: boolean
  overallProgress: { stage: string; progress: number }
}) => {
  const isStatusComplete = params.resolvedStatus === 'complete'
  return (
    !params.hasFailedStages &&
    ((params.completed && Boolean(params.urlArtifactId)) ||
      isStatusComplete ||
      (params.isComplete &&
        params.overallProgress.stage === 'complete' &&
        params.overallProgress.progress === 100))
  )
}
