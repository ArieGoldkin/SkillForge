/**
 * Dedupe library search items by analysis_id while preserving order.
 */
export function dedupeByAnalysisId<T extends { analysis_id: string }>(items: T[]): T[] {
  const seen = new Set<string>()
  const deduped: T[] = []

  for (const item of items) {
    if (seen.has(item.analysis_id)) continue
    seen.add(item.analysis_id)
    deduped.push(item)
  }

  return deduped
}
