# Artifact Visualization Guide

## Quick Start

To visualize any artifact, use the script:

```bash
# View the most recent artifact
python backend/scripts/visualize_artifact.py --latest

# View by analysis ID (from your LangSmith trace)
python backend/scripts/visualize_artifact.py --analysis-id <analysis_id>

# View by artifact ID
python backend/scripts/visualize_artifact.py --artifact-id <artifact_id>
```

## What You'll See

The visualization script shows:

### 1. Artifact Information Panel
```
================================================================================
  Artifact Information
================================================================================
  ID:              123e4567-e89b-12d3-a456-426614174000
  Analysis ID:     abc12345-e89b-12d3-a456-426614174000
  Version:         1
  Created At:      2025-01-15 10:30:00+00:00
  Download Count:  5
  Content Size:    45.2 KB
  Line Count:      523

  Metadata:
  {
      "topics": ["react", "streaming", "ssr"],
      "tags": ["frontend", "performance"],
      "complexity_score": 7.5
  }
```

### 2. Markdown Structure Analysis
```
================================================================================
  Markdown Structure
================================================================================
  Headings:        12
  Code Blocks:     8
  Links:           15
  List Items:      45
  Tables:          2

  Document Outline:
  # Implementation Guide: React 19 Streaming SSR
    ## Executive Summary
      ### Overview
    ## Key Findings
    ## Technical Analysis
    ## Implementation Plan
      ### Step 1: Setup
      ### Step 2: Configuration
    ## Claude Code Prompt
    ## Considerations
    ## References
```

### 3. Content Preview
```
================================================================================
  Markdown Preview (First 50 lines)
================================================================================
   1 | # Implementation Guide: React 19 Streaming SSR
   2 |
   3 | ## Executive Summary
   4 |
   5 | React 19 introduces powerful streaming server-side rendering capabilities
   6 | that enable progressive content delivery and improved performance...
   7 |
   8 | ## Key Findings
   9 |
  10 | - **Streaming SSR**: React 19's new `renderToReadableStream` API enables
  11 |   progressive rendering...
  12 | - **Suspense Boundaries**: Improved error boundaries and loading states...
  13 | - **Performance**: 40% reduction in Time to Interactive...
  14 |
  15 | ## Technical Analysis
  16 |
  17 | ### Architecture Overview
  18 |
  19 | React 19's streaming SSR works by:
  20 |
  21 | 1. Rendering components in chunks
  22 | 2. Streaming HTML to the client
  23 | 3. Hydrating progressively...
  24 |
  25 | ```typescript
  26 | import { renderToReadableStream } from 'react-dom/server';
  27 |
  28 | async function handleRequest(request: Request) {
  29 |   const stream = await renderToReadableStream(<App />);
  30 |   return new Response(stream, {
  31 |     headers: { 'Content-Type': 'text/html' }
  32 |   });
  33 | }
  34 | ```
  35 |
  36 | ### Implementation Details
  37 |
  38 | ... (more content)
  39 |
... (50 more lines)
```

## Example: Complete Visualization Output

Here's what a full visualization looks like:

```
================================================================================
  ARTIFACT VISUALIZATION
================================================================================

================================================================================
  Artifact Information
================================================================================
  ID:              a1b2c3d4-e5f6-7890-abcd-ef1234567890
  Analysis ID:     bcab7522-eb5e-4633-a891-b0b842b2544f
  Version:         1
  Created At:      2025-01-15 14:23:45+00:00
  Download Count:  0
  Content Size:    38.5 KB
  Line Count:      487

  Metadata:
  {
      "topics": ["react", "streaming", "ssr"],
      "tags": ["frontend", "performance"],
      "complexity_score": 7.5,
      "estimated_read_time_minutes": 12
  }

================================================================================
  Markdown Structure
================================================================================
  Headings:        15
  Code Blocks:     12
  Links:           23
  List Items:      67
  Tables:          3

  Document Outline:
  # Implementation Guide: React 19 Streaming SSR
    ## Executive Summary
    ## Key Findings
    ## Technical Analysis
      ### Architecture Overview
      ### Performance Characteristics
      ### Compatibility Considerations
    ## Implementation Plan
      ### Step 1: Setup Environment
      ### Step 2: Configure Server
      ### Step 3: Update Components
      ### Step 4: Testing
    ## Claude Code Prompt
    ## Considerations
      ### Browser Support
      ### Performance Trade-offs
    ## References

================================================================================
  Markdown Preview (First 50 lines)
================================================================================
   1 | # Implementation Guide: React 19 Streaming SSR
   2 |
   3 | > Generated from analysis of: https://react.dev/blog/2024/04/25/react-19
   4 |
   5 | ## Executive Summary
   6 |
   7 | React 19 introduces powerful streaming server-side rendering capabilities
   8 | that enable progressive content delivery and significantly improve Core
   9 | Web Vitals metrics. The new `renderToReadableStream` API allows servers
  10 | to stream HTML to clients as components render, reducing Time to First
  11 | Byte (TTFB) and Time to Interactive (TTI).
  12 |
  13 | ## Key Findings
  14 |
  15 | ### Streaming SSR Architecture
  16 |
  17 | - **Progressive Rendering**: Components render in chunks as data becomes
  18 |   available, allowing faster initial paint
  19 | - **Suspense Integration**: Seamless integration with React Suspense for
  20 |   loading states and error boundaries
  21 | - **Selective Hydration**: Only interactive components hydrate, reducing
  22 |   JavaScript bundle size
  23 |
  24 | ### Performance Improvements
  25 |
  25 | - **40% reduction** in Time to Interactive (TTI)
  26 | - **60% improvement** in Largest Contentful Paint (LCP)
  27 | - **50% reduction** in JavaScript bundle size for initial render
  28 |
  29 | ## Technical Analysis
  30 |
  31 | ### Architecture Overview
  32 |
  33 | React 19's streaming SSR works by rendering components asynchronously and
  34 | streaming HTML chunks to the client. The key innovation is the ability to
  35 | pause and resume rendering based on data availability.
  36 |
  37 | ```typescript
  38 | import { renderToReadableStream } from 'react-dom/server';
  39 | import { Suspense } from 'react';
  40 |
  41 | async function App() {
  42 |   const data = await fetchData();
  43 |   return <Content data={data} />;
  44 | }
  45 |
  46 | async function handleRequest(request: Request) {
  47 |   const stream = await renderToReadableStream(
  48 |     <Suspense fallback={<Loading />}>
  49 |       <App />
  50 |     </Suspense>
  51 |   );
  52 |
  53 |   return new Response(stream, {
  54 |     headers: { 'Content-Type': 'text/html' }
  55 |   });
  56 | }
  57 | ```
  58 |
  59 | ... (remaining lines)
  60 |

================================================================================
  Export Options
================================================================================
  To save full content to file:
    echo '...' > artifact_a1b2c3d4-e5f6-7890-abcd-ef1234567890.md

  Or view in browser (markdown viewer)
    python scripts/visualize_artifact.py --artifact-id a1b2c3d4-e5f6-7890-abcd-ef1234567890 --save output.md
```

## Visual Structure Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    ARTIFACT VISUALIZATION                    │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Metadata   │   │   Structure  │   │   Preview    │
│              │   │              │   │              │
│ • ID         │   │ • Headings   │   │ • First 50   │
│ • Analysis   │   │ • Code       │   │   lines      │
│   ID         │   │ • Links      │   │              │
│ • Version    │   │ • Lists      │   │ • Line       │
│ • Size       │   │ • Tables     │   │   numbers    │
│ • Downloads  │   │ • Outline    │   │              │
│ • Metadata   │   │              │   │ • Full with  │
│              │   │              │   │   --full     │
└──────────────┘   └──────────────┘   └──────────────┘
```

## Usage Examples

### Example 1: View Latest Artifact
```bash
$ python backend/scripts/visualize_artifact.py --latest

Fetching latest artifact...
[Shows full visualization]
```

### Example 2: View by Analysis ID
```bash
$ python backend/scripts/visualize_artifact.py --analysis-id bcab7522-eb5e-4633-a891-b0b842b2544f

Fetching artifact for analysis bcab7522-eb5e-4633-a891-b0b842b2544f...
[Shows full visualization]
```

### Example 3: Save to File
```bash
$ python backend/scripts/visualize_artifact.py --artifact-id a1b2c3d4-e5f6-7890-abcd-ef1234567890 --save my-artifact.md

✅ Artifact saved to my-artifact.md
   Size: 38.5 KB
```

### Example 4: View Full Content
```bash
$ python backend/scripts/visualize_artifact.py --artifact-id a1b2c3d4-e5f6-7890-abcd-ef1234567890 --full

[Shows complete markdown content in terminal]
```

## Integration with LangSmith Trace

To visualize an artifact from a LangSmith trace:

1. **Get Analysis ID** from your trace URL or trace metadata
2. **Run visualization script**:
   ```bash
   python backend/scripts/visualize_artifact.py --analysis-id <analysis_id>
   ```
3. **View structure** to understand what was generated
4. **Save to file** if you want to read it locally:
   ```bash
   python backend/scripts/visualize_artifact.py --analysis-id <analysis_id> --save artifact.md
   ```

## Tips

- **Use `--latest`** to quickly see the most recent artifact
- **Use `--full`** to see complete markdown (good for reading)
- **Use `--save`** to export and view in your favorite markdown viewer
- **Check metadata** to see topics, complexity score, and tags
- **Review outline** to quickly understand document structure

