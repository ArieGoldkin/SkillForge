# API Specification: Library Search Endpoint

## Overview

This document provides the complete API specification for the library search endpoint, including request parameters, response formats, error handling, and usage examples.

## Base URL

```
Production: https://api.skillforge.com/api/v1
Development: http://localhost:8500/api/v1
```

## Endpoint

### GET /library

Search and list analyses from the library with support for full-text search, semantic search, and hybrid search modes.

---

## Request

### HTTP Method
```
GET /api/v1/library
```

### Query Parameters

| Parameter | Type | Required | Default | Constraints | Description |
|-----------|------|----------|---------|-------------|-------------|
| `query` | string | No | `null` | Max 1000 chars | Search query text. If omitted, returns paginated list. |
| `search_mode` | string | No | `"hybrid"` | `hybrid` \| `fulltext` \| `semantic` | Search mode to use. |
| `content_type` | string | No | `null` | `article` \| `video` \| `repo` | Filter results by content type. |
| `status` | string | No | `null` | `pending` \| `complete` \| `failed` | Filter results by analysis status. |
| `limit` | integer | No | `20` | Min: 1, Max: 100 | Maximum number of results to return. |
| `offset` | integer | No | `0` | Min: 0 | Number of results to skip (for pagination). |

### Parameter Details

#### `query` (string, optional)

The search query text. Behavior varies by search mode:

- **Full-Text Mode**: Matches keywords using PostgreSQL full-text search
- **Semantic Mode**: Finds conceptually similar content using vector embeddings
- **Hybrid Mode**: Combines both approaches using RRF (Reciprocal Rank Fusion)

**Examples**:
- `"React hooks"` - Simple keyword search
- `"React hooks useState useEffect"` - Multiple keywords
- `"async/await programming"` - Special characters handled safely

**Constraints**:
- Maximum length: 1000 characters
- Empty or whitespace-only queries are treated as no query (returns listing)
- Special characters and unicode are supported

#### `search_mode` (string, optional)

Search mode determines how results are ranked and returned.

**Modes**:

1. **`hybrid`** (default): Combines full-text and semantic search using RRF
   - Best for: General-purpose search
   - Performance: < 750ms (p95)
   - Weights: 0.7 × full-text + 0.3 × semantic

2. **`fulltext`**: PostgreSQL full-text search with GIN index
   - Best for: Exact keyword matching
   - Performance: < 500ms (p95)
   - Uses weighted fields: title (A) > url (B) > content (C)

3. **`semantic`**: Vector similarity search using embeddings
   - Best for: Conceptual similarity
   - Performance: < 750ms (p95)
   - Uses OpenAI text-embedding-3-small (1536 dimensions)

#### `content_type` (string, optional)

Filter results by content type.

**Valid Values**:
- `"article"` - Web articles and blog posts
- `"video"` - Video content (YouTube, Vimeo, etc.)
- `"repo"` - Code repositories (GitHub, GitLab, etc.)

**Example**: `content_type=article`

#### `status` (string, optional)

Filter results by analysis status.

**Valid Values**:
- `"pending"` - Analysis queued but not started
- `"complete"` - Analysis finished successfully
- `"failed"` - Analysis failed with errors

**Example**: `status=complete`

#### `limit` (integer, optional)

Maximum number of results to return. Used for pagination.

**Constraints**:
- Minimum: 1
- Maximum: 100
- Default: 20

**Example**: `limit=50`

#### `offset` (integer, optional)

Number of results to skip. Used for pagination.

**Constraints**:
- Minimum: 0
- Default: 0

**Example**: `offset=20` (skip first 20 results)

---

## Response

### Success Response (200 OK)

```json
{
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "url": "https://example.com/react-hooks-intro",
      "title": "Introduction to React Hooks",
      "content_type": "article",
      "status": "complete",
      "created_at": "2025-12-04T10:30:00Z",
      "relevance_score": 0.95
    },
    {
      "id": "234e5678-e89b-12d3-a456-426614174001",
      "url": "https://example.com/hooks-guide",
      "title": "Complete Guide to React Hooks",
      "content_type": "article",
      "status": "complete",
      "created_at": "2025-12-03T14:20:00Z",
      "relevance_score": 0.87
    }
  ],
  "total": 142,
  "limit": 20,
  "offset": 0,
  "search_mode": "hybrid"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `results` | array | Array of library items matching the search criteria |
| `total` | integer | Total number of results matching the query (across all pages) |
| `limit` | integer | Limit applied to this request |
| `offset` | integer | Offset applied to this request |
| `search_mode` | string | Search mode used for this request |

### Library Item Fields

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | string (UUID) | No | Unique identifier for the analysis |
| `url` | string | No | Source URL that was analyzed |
| `title` | string | Yes | Title extracted from content (may be null) |
| `content_type` | string | No | Type of content: `article`, `video`, or `repo` |
| `status` | string | No | Analysis status: `pending`, `complete`, or `failed` |
| `created_at` | string (ISO 8601) | No | Timestamp when analysis was created |
| `relevance_score` | number | Yes | Relevance score (0-1). Only present for search results, not listings. |

---

## Error Responses

### 400 Bad Request

Returned when request parameters are invalid.

```json
{
  "detail": "Invalid search_mode. Must be one of: hybrid, fulltext, semantic"
}
```

**Common Causes**:
- Invalid `search_mode` value
- Invalid `content_type` value
- Invalid `status` value
- `limit` out of range (< 1 or > 100)
- `offset` is negative

**Example**:
```bash
curl -X GET "http://localhost:8500/api/v1/library?search_mode=invalid"

# Response: 400 Bad Request
{
  "detail": "Invalid search_mode. Must be one of: hybrid, fulltext, semantic"
}
```

### 500 Internal Server Error

Returned when server encounters an unexpected error.

```json
{
  "detail": "Library search failed"
}
```

**Common Causes**:
- Database connection failure
- Embedding service unavailable (semantic search)
- Internal server error

**Note**: Error details are logged but not exposed to clients for security.

---

## Usage Examples

### Example 1: Hybrid Search (Default)

Search for "React hooks" using hybrid mode (combines full-text and semantic search).

**Request**:
```bash
curl -X GET "http://localhost:8500/api/v1/library?query=React%20hooks&limit=10"
```

**Response**:
```json
{
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "url": "https://example.com/react-hooks",
      "title": "Introduction to React Hooks",
      "content_type": "article",
      "status": "complete",
      "created_at": "2025-12-04T10:30:00Z",
      "relevance_score": null
    }
  ],
  "total": 42,
  "limit": 10,
  "offset": 0,
  "search_mode": "hybrid"
}
```

### Example 2: Full-Text Search Only

Search using only PostgreSQL full-text search for exact keyword matching.

**Request**:
```bash
curl -X GET "http://localhost:8500/api/v1/library?query=React%20hooks&search_mode=fulltext&limit=5"
```

**Response**:
```json
{
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "url": "https://example.com/react-hooks",
      "title": "Introduction to React Hooks",
      "content_type": "article",
      "status": "complete",
      "created_at": "2025-12-04T10:30:00Z",
      "relevance_score": 0.95
    },
    {
      "id": "234e5678-e89b-12d3-a456-426614174001",
      "url": "https://example.com/hooks-guide",
      "title": "Complete Guide to React Hooks",
      "content_type": "article",
      "status": "complete",
      "created_at": "2025-12-03T14:20:00Z",
      "relevance_score": 0.87
    }
  ],
  "total": 5,
  "limit": 5,
  "offset": 0,
  "search_mode": "fulltext"
}
```

**Note**: Full-text search returns `relevance_score` based on PostgreSQL's `ts_rank()`.

### Example 3: Semantic Search Only

Search using vector similarity for conceptually similar content.

**Request**:
```bash
curl -X GET "http://localhost:8500/api/v1/library?query=React%20hooks&search_mode=semantic&limit=5"
```

**Response**:
```json
{
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "url": "https://example.com/react-hooks",
      "title": "Introduction to React Hooks",
      "content_type": "article",
      "status": "complete",
      "created_at": "2025-12-04T10:30:00Z",
      "relevance_score": null
    },
    {
      "id": "345e6789-e89b-12d3-a456-426614174002",
      "url": "https://example.com/vue-composition",
      "title": "Vue Composition API Guide",
      "content_type": "article",
      "status": "complete",
      "created_at": "2025-12-02T09:15:00Z",
      "relevance_score": null
    }
  ],
  "total": 5,
  "limit": 5,
  "offset": 0,
  "search_mode": "semantic"
}
```

**Note**: Semantic search may return conceptually similar content (e.g., Vue Composition API for "React hooks" query).

### Example 4: List All Analyses (No Search)

Get a paginated list of all analyses without searching.

**Request**:
```bash
curl -X GET "http://localhost:8500/api/v1/library?limit=20&offset=0"
```

**Response**:
```json
{
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "url": "https://example.com/article1",
      "title": "Article 1",
      "content_type": "article",
      "status": "complete",
      "created_at": "2025-12-04T10:30:00Z",
      "relevance_score": null
    },
    {
      "id": "234e5678-e89b-12d3-a456-426614174001",
      "url": "https://example.com/article2",
      "title": "Article 2",
      "content_type": "video",
      "status": "complete",
      "created_at": "2025-12-03T14:20:00Z",
      "relevance_score": null
    }
  ],
  "total": 1523,
  "limit": 20,
  "offset": 0,
  "search_mode": "hybrid"
}
```

**Note**: When no query is provided, results are ordered by `created_at` descending.

### Example 5: Filter by Content Type

Search for articles only.

**Request**:
```bash
curl -X GET "http://localhost:8500/api/v1/library?query=React&content_type=article&limit=10"
```

**Response**:
```json
{
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "url": "https://example.com/react-article",
      "title": "React Tutorial",
      "content_type": "article",
      "status": "complete",
      "created_at": "2025-12-04T10:30:00Z",
      "relevance_score": null
    }
  ],
  "total": 34,
  "limit": 10,
  "offset": 0,
  "search_mode": "hybrid"
}
```

**Note**: All results have `content_type: "article"`.

### Example 6: Filter by Status

Search for completed analyses only.

**Request**:
```bash
curl -X GET "http://localhost:8500/api/v1/library?query=React&status=complete&limit=10"
```

**Response**:
```json
{
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "url": "https://example.com/react-tutorial",
      "title": "React Tutorial",
      "content_type": "article",
      "status": "complete",
      "created_at": "2025-12-04T10:30:00Z",
      "relevance_score": null
    }
  ],
  "total": 89,
  "limit": 10,
  "offset": 0,
  "search_mode": "hybrid"
}
```

**Note**: All results have `status: "complete"`.

### Example 7: Pagination (Page 2)

Get the second page of results (offset 20, limit 20).

**Request**:
```bash
curl -X GET "http://localhost:8500/api/v1/library?query=React&limit=20&offset=20"
```

**Response**:
```json
{
  "results": [
    {
      "id": "456e7890-e89b-12d3-a456-426614174003",
      "url": "https://example.com/react-page2-item1",
      "title": "React Advanced Topics",
      "content_type": "article",
      "status": "complete",
      "created_at": "2025-12-01T08:00:00Z",
      "relevance_score": null
    }
  ],
  "total": 142,
  "limit": 20,
  "offset": 20,
  "search_mode": "hybrid"
}
```

**Note**: `total` remains consistent across pages. Use `offset = page_number * limit` for pagination.

### Example 8: Combined Filters

Search for completed articles about React.

**Request**:
```bash
curl -X GET "http://localhost:8500/api/v1/library?query=React&content_type=article&status=complete&search_mode=fulltext&limit=10"
```

**Response**:
```json
{
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "url": "https://example.com/react-article",
      "title": "Complete React Guide",
      "content_type": "article",
      "status": "complete",
      "created_at": "2025-12-04T10:30:00Z",
      "relevance_score": 0.95
    }
  ],
  "total": 23,
  "limit": 10,
  "offset": 0,
  "search_mode": "fulltext"
}
```

### Example 9: Empty Results

Search with no matching results.

**Request**:
```bash
curl -X GET "http://localhost:8500/api/v1/library?query=nonexistentquery12345&search_mode=fulltext"
```

**Response**:
```json
{
  "results": [],
  "total": 0,
  "limit": 20,
  "offset": 0,
  "search_mode": "fulltext"
}
```

---

## Pagination

### Pagination Strategy

Use `limit` and `offset` parameters to implement pagination:

```
Page 1: offset=0, limit=20   (results 1-20)
Page 2: offset=20, limit=20  (results 21-40)
Page 3: offset=40, limit=20  (results 41-60)
...
```

### Pagination Formula

```python
page_number = 1  # 1-indexed
limit = 20
offset = (page_number - 1) * limit
```

### Total Pages Calculation

```python
total_pages = ceil(total / limit)
```

### Example Pagination Implementation (JavaScript)

```javascript
async function fetchPage(pageNumber, limit = 20) {
  const offset = (pageNumber - 1) * limit;
  const response = await fetch(
    `/api/v1/library?query=React&limit=${limit}&offset=${offset}`
  );
  const data = await response.json();

  return {
    results: data.results,
    currentPage: pageNumber,
    totalPages: Math.ceil(data.total / limit),
    totalResults: data.total,
  };
}

// Fetch page 1
const page1 = await fetchPage(1);
console.log(`Page 1 of ${page1.totalPages}`);

// Fetch page 2
const page2 = await fetchPage(2);
console.log(`Page 2 of ${page2.totalPages}`);
```

### Best Practices

1. **Limit Maximum Offset**: For very large offsets (> 10,000), consider cursor-based pagination
2. **Cache Total Count**: Total count may change between requests; consider caching
3. **Validate Pages**: Check if `offset` < `total` before fetching
4. **Default Limits**: Use reasonable default (20) to prevent large responses

---

## Performance Characteristics

### Latency Targets (p95)

| Operation | Target | Typical |
|-----------|--------|---------|
| Full-text search | < 500ms | ~200ms |
| Semantic search | < 750ms | ~400ms |
| Hybrid search | < 750ms | ~500ms |
| Library listing | < 200ms | ~50ms |

### Throughput

- **Concurrent Requests**: Supports 50+ concurrent searches
- **Rate Limit**: 100 requests/minute per IP (configurable)
- **Connection Pool**: 20 connections, 10 overflow

### Caching Strategy

- **Query Embeddings**: Cached for 5 minutes (semantic/hybrid search)
- **Result Sets**: Not cached by default (consider client-side caching)
- **Total Counts**: Recalculated on each request

---

## Security Considerations

### Input Validation

- **Query Length**: Limited to 1000 characters
- **Parameter Validation**: Enums validated against whitelist
- **SQL Injection**: Prevented by parameterized queries
- **XSS Protection**: Special characters escaped in responses

### Rate Limiting

```
Default Limits:
- 100 requests/minute per IP
- 1000 requests/hour per user
```

**Rate Limit Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1609459200
```

**Rate Limit Exceeded (429)**:
```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds."
}
```

### Authentication

Currently, this endpoint is **unauthenticated**. For production, consider:

- API key authentication
- JWT token authentication
- OAuth 2.0 integration

---

## OpenAPI Specification

### OpenAPI 3.0 Schema

```yaml
openapi: 3.0.0
info:
  title: SkillForge API
  version: 1.0.0
  description: Analysis library search and discovery API

paths:
  /api/v1/library:
    get:
      summary: Search and list analyses
      description: |
        Search and list analyses from the library with support for
        full-text search, semantic search, and hybrid search modes.
      parameters:
        - name: query
          in: query
          description: Search query text
          required: false
          schema:
            type: string
            maxLength: 1000
        - name: search_mode
          in: query
          description: Search mode (hybrid, fulltext, semantic)
          required: false
          schema:
            type: string
            enum: [hybrid, fulltext, semantic]
            default: hybrid
        - name: content_type
          in: query
          description: Filter by content type
          required: false
          schema:
            type: string
            enum: [article, video, repo]
        - name: status
          in: query
          description: Filter by status
          required: false
          schema:
            type: string
            enum: [pending, complete, failed]
        - name: limit
          in: query
          description: Maximum number of results
          required: false
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 20
        - name: offset
          in: query
          description: Number of results to skip
          required: false
          schema:
            type: integer
            minimum: 0
            default: 0
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/LibraryResponse'
        '400':
          description: Bad request - invalid parameters
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

components:
  schemas:
    LibraryResponse:
      type: object
      required:
        - results
        - total
        - limit
        - offset
        - search_mode
      properties:
        results:
          type: array
          items:
            $ref: '#/components/schemas/LibraryItem'
        total:
          type: integer
          description: Total number of results
        limit:
          type: integer
          description: Limit applied to query
        offset:
          type: integer
          description: Offset applied to query
        search_mode:
          type: string
          enum: [hybrid, fulltext, semantic]
          description: Search mode used

    LibraryItem:
      type: object
      required:
        - id
        - url
        - content_type
        - status
        - created_at
      properties:
        id:
          type: string
          format: uuid
          description: Unique identifier
        url:
          type: string
          description: Source URL
        title:
          type: string
          nullable: true
          description: Content title
        content_type:
          type: string
          enum: [article, video, repo]
          description: Type of content
        status:
          type: string
          enum: [pending, complete, failed]
          description: Analysis status
        created_at:
          type: string
          format: date-time
          description: Creation timestamp (ISO 8601)
        relevance_score:
          type: number
          nullable: true
          description: Relevance score (0-1)

    ErrorResponse:
      type: object
      required:
        - detail
      properties:
        detail:
          type: string
          description: Error message
```

---

## Interactive API Documentation

Once deployed, interactive API documentation is available at:

```
Swagger UI: http://localhost:8500/docs
ReDoc: http://localhost:8500/redoc
```

These interfaces allow you to:
- Browse all endpoints
- Try API calls directly from the browser
- View request/response schemas
- Download OpenAPI specification

---

## Client Libraries

### Python Example

```python
import httpx

async def search_library(
    query: str,
    search_mode: str = "hybrid",
    limit: int = 20,
    offset: int = 0,
):
    """Search the library using the API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8500/api/v1/library",
            params={
                "query": query,
                "search_mode": search_mode,
                "limit": limit,
                "offset": offset,
            },
        )
        response.raise_for_status()
        return response.json()

# Usage
results = await search_library("React hooks", search_mode="hybrid", limit=10)
print(f"Found {results['total']} results")
for item in results["results"]:
    print(f"- {item['title']}")
```

### JavaScript/TypeScript Example

```typescript
interface LibrarySearchParams {
  query?: string;
  searchMode?: 'hybrid' | 'fulltext' | 'semantic';
  contentType?: 'article' | 'video' | 'repo';
  status?: 'pending' | 'complete' | 'failed';
  limit?: number;
  offset?: number;
}

interface LibraryItem {
  id: string;
  url: string;
  title: string | null;
  content_type: string;
  status: string;
  created_at: string;
  relevance_score: number | null;
}

interface LibraryResponse {
  results: LibraryItem[];
  total: number;
  limit: number;
  offset: number;
  search_mode: string;
}

async function searchLibrary(
  params: LibrarySearchParams
): Promise<LibraryResponse> {
  const queryParams = new URLSearchParams();

  if (params.query) queryParams.append('query', params.query);
  if (params.searchMode) queryParams.append('search_mode', params.searchMode);
  if (params.contentType) queryParams.append('content_type', params.contentType);
  if (params.status) queryParams.append('status', params.status);
  if (params.limit) queryParams.append('limit', params.limit.toString());
  if (params.offset) queryParams.append('offset', params.offset.toString());

  const response = await fetch(
    `http://localhost:8500/api/v1/library?${queryParams}`
  );

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

// Usage
const results = await searchLibrary({
  query: 'React hooks',
  searchMode: 'hybrid',
  limit: 10,
});

console.log(`Found ${results.total} results`);
results.results.forEach((item) => {
  console.log(`- ${item.title}`);
});
```

---

## Changelog

### Version 1.0.0 (2025-12-04)

- Initial release of library search endpoint
- Support for hybrid, full-text, and semantic search modes
- Filtering by content_type and status
- Pagination support
- RRF-based hybrid search with configurable weights

---

## Future Enhancements

Planned improvements for future versions:

1. **Cursor-Based Pagination**: For more efficient deep pagination
2. **Search Suggestions**: Auto-complete and query suggestions
3. **Faceted Search**: Aggregations by content_type, date, etc.
4. **Advanced Filters**: Date ranges, custom fields
5. **Saved Searches**: User-specific saved search queries
6. **Search Analytics**: Popular queries and click-through tracking
7. **Export Functionality**: Export search results to CSV/JSON

---

## Support

For questions or issues:

- **Documentation**: https://docs.skillforge.com
- **API Status**: https://status.skillforge.com
- **GitHub Issues**: https://github.com/skillforge/backend/issues
- **Email**: support@skillforge.com
