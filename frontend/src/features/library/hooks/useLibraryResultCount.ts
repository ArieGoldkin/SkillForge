interface UseLibraryResultCountParams {
  filteredSkillsCount: number
  searchQuery: string
  searchResults?: {
    pages?: Array<{ total?: number }>
  }
}

export function useLibraryResultCount({
  filteredSkillsCount,
  searchQuery,
  searchResults,
}: UseLibraryResultCountParams) {
  const showingCount = filteredSkillsCount
  const totalCount = searchQuery.trim()
    ? showingCount
    : (searchResults?.pages?.[0]?.total ?? filteredSkillsCount)

  return {
    showingCount,
    totalCount,
  }
}
