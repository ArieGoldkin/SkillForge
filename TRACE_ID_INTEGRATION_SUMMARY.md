# Trace ID Integration Summary

## Problem
Direct URL navigation (bookmarks, browser refresh) to `/artifact/:artifactId` lost the `trace_id` because it was only available via React Router's `location.state`, which is cleared on direct navigation.

## Solution
Fetch `trace_id` from the backend API and include it in the artifact metadata response. The frontend now retrieves `trace_id` from the API instead of relying solely on navigation state.

## Changes Made

### Backend Changes

#### 1. Updated Schema (`backend/app/domains/analysis/schemas/api.py`)
```python
class ArtifactMetadataResponse(BaseModel):
    """Metadata and content for an artifact."""

    artifact_id: str = Field(..., description="Artifact identifier")
    analysis_id: str = Field(..., description="Parent analysis identifier")
    markdown_content: str = Field(..., description="Artifact markdown content")
    artifact_metadata: dict | None = Field(None, description="Optional artifact metadata")
    trace_id: str | None = Field(None, description="Langfuse trace ID for feedback")  # NEW
    created_at: str = Field(..., description="Creation timestamp")
```

#### 2. Updated Endpoint Responses (`backend/app/api/v1/analysis/artifacts.py`)
Both `get_artifact_by_analysis()` and `get_artifact_by_id()` now return `trace_id`:

```python
return ArtifactMetadataResponse(
    artifact_id=str(artifact.id),
    analysis_id=str(artifact.analysis_id),
    markdown_content=str(cast(str | None, artifact.markdown_content) or ""),
    artifact_metadata=cast(dict[str, object] | None, artifact.artifact_metadata)
    if artifact.artifact_metadata
    else None,
    trace_id=artifact.trace_id,  # NEW
    created_at=artifact.created_at.isoformat() if artifact.created_at else "",
)
```

### Frontend Changes

#### 3. Updated TypeScript Interface (`frontend/src/types/api.ts`)
```typescript
export interface ArtifactMetadataResponse {
  analysis_id: string
  artifact_id: string
  markdown_content?: string | null
  metadata?: Record<string, unknown>
  trace_id?: string | null  // NEW
  download_count?: number
  created_at?: string
}
```

#### 4. Added New API Method (`frontend/src/services/api.service.ts`)
```typescript
/**
 * Get artifact metadata by artifact ID
 * GET /api/v1/artifacts/{artifact_id}
 * Returns artifact metadata including trace_id
 */
getArtifactById: async (artifactId: string): Promise<ArtifactMetadataResponse | null> => {
  try {
    return await apiFetch<ArtifactMetadataResponse>(`/api/v1/artifacts/${artifactId}`)
  } catch (error) {
    console.warn(`getArtifactById failed for ${artifactId}:`, error)
    return null
  }
},
```

#### 5. Updated Hook to Fetch Metadata (`frontend/src/features/artifact/hooks/useArtifact.ts`)
```typescript
export interface UseArtifactReturn extends UseArtifactState {
  content: string | null
  traceId: string | null  // NEW
  isLoading: boolean
  error: Error | null
  download: () => void
}

async function fetchArtifact(artifactId: string): Promise<ArtifactMetadataResponse> {
  const metadata = await analyzeAPI.getArtifactById(artifactId)  // CHANGED from downloadArtifact
  if (!metadata) {
    throw new Error('Failed to load artifact metadata')
  }
  return metadata
}

export function useArtifact(artifactId: string | undefined): UseArtifactReturn {
  // ... query logic ...

  return {
    content: data?.markdown_content ?? null,
    traceId: data?.trace_id ?? null,  // NEW
    isLoading,
    error: artifactId ? (error as Error | null) : new Error('No artifact ID provided'),
    download,
  }
}
```

#### 6. Updated Page Component (`frontend/src/features/artifact/ArtifactPage.tsx`)
```typescript
export default function ArtifactPage() {
  const routeApi = getRouteApi('/artifact/$artifactId')
  const { artifactId } = routeApi.useParams()
  const { analysisId } = routeApi.useSearch()
  const location = useLocation()

  // Get trace_id from both sources
  const locationStateTraceId = (location.state as { traceId?: string } | undefined)?.traceId
  const { content, traceId: apiTraceId, isLoading, error, download } = useArtifact(artifactId)

  // Prefer API trace_id, fallback to location.state for SSE flows
  const traceId = apiTraceId ?? locationStateTraceId ?? null

  return (
    // ... JSX with FeedbackButtons receiving traceId ...
  )
}
```

## Behavior

### Before
- Fresh analysis: trace_id passed via SSE → location.state → FeedbackButtons ✅
- Direct URL: No location.state → trace_id = undefined → No feedback possible ❌

### After
- Fresh analysis: trace_id from API (fallback to location.state) → FeedbackButtons ✅
- Direct URL: trace_id fetched from API → FeedbackButtons ✅
- Bookmark: trace_id fetched from API → FeedbackButtons ✅
- Browser refresh: trace_id fetched from API → FeedbackButtons ✅

## Files Modified

### Backend
1. `backend/app/domains/analysis/schemas/api.py` - Added `trace_id` field to schema
2. `backend/app/api/v1/analysis/artifacts.py` - Return `trace_id` in both endpoints

### Frontend
1. `frontend/src/types/api.ts` - Added `trace_id` to interface
2. `frontend/src/services/api.service.ts` - Added `getArtifactById()` method
3. `frontend/src/features/artifact/hooks/useArtifact.ts` - Fetch metadata instead of raw content, return `traceId`
4. `frontend/src/features/artifact/ArtifactPage.tsx` - Use API-fetched `traceId` with fallback

## Testing Checklist

- [ ] Fresh analysis flow: Verify trace_id is available for feedback
- [ ] Direct URL navigation: `/artifact/abc123` should fetch trace_id from API
- [ ] Browser refresh: trace_id should persist after refresh
- [ ] Bookmark: Saved URLs should still show feedback buttons with valid trace_id
- [ ] No trace_id case: Feedback buttons should gracefully handle null trace_id (disable feedback or show message)

## Notes

- The database model already had `trace_id` column, no migration needed
- `location.state` is kept as a fallback for SSE flows where trace_id may be available before API fetch completes
- The API endpoint `GET /api/v1/artifacts/{id}` already existed (added in issue #385), we just added a frontend method to call it
