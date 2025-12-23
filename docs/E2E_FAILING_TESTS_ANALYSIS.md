# E2E Test Failures - Detailed Root Cause Analysis

**Date**: December 22, 2025  
**Status**: 3 tests failing (down from 28)  
**Context**: After fixing navigation and request context disposal issues

---

## Executive Summary

After fixing the critical navigation and request context disposal issues, we're left with **3 failing tests** that represent different categories of problems:

1. **UI Element Selector Mismatch** - Analysis page heading not found
2. **Content Structure Issue** - Artifact markdown has no code blocks
3. **Backend Workflow Execution** - Workflow stages not being emitted via SSE

These are **separate issues** from the navigation/context problems we fixed. Each requires different investigation and fixes.

---

## Failure #1: Analysis Metadata Heading Not Found

**Test**: `analysis.spec.ts:113` - "should display analysis metadata"  
**Error**: 
```
Locator: getByRole('heading', { name: /content analysis/i })
Expected: visible
Timeout: 5000ms
Error: element(s) not found
```

### Root Cause Analysis

**What the test expects:**
```typescript
await expect(page.getByRole('heading', { name: /content analysis/i })).toBeVisible();
```

**What the code actually renders:**
```tsx
// frontend/src/features/analysis/components/steps/AnalysisHeader.tsx:56
<h1 className="text-3xl font-bold">{title || 'Content Analysis'}</h1>
```

**The Problem:**
- The `<h1>` element **does exist** and contains "Content Analysis" text
- However, `getByRole('heading', { name: /content analysis/i })` is **not finding it**
- This suggests either:
  1. The heading is not visible when the test runs (timing issue)
  2. The heading text doesn't match the regex (case/whitespace issue)
  3. The heading is rendered but not accessible via role (ARIA issue)

**Investigation Needed:**
1. Check if `AnalysisHeader` is actually rendered when the test runs
2. Verify the heading is visible (not hidden by CSS or loading states)
3. Check if there's a timing issue - the heading might load after the test timeout
4. Verify the actual text content matches the regex pattern

**Code Locations:**
- Test: `frontend/e2e/specs/analysis.spec.ts:113-125`
- Component: `frontend/src/features/analysis/components/steps/AnalysisHeader.tsx:56`
- Usage: `frontend/src/features/analysis/components/render-router/AnalysisRenderRouter.tsx:131`

**Possible Fixes:**
1. **Increase timeout** - But user said "never increase timeouts" - so this is NOT the solution
2. **Wait for component to render** - Add explicit wait for `AnalysisHeader` to be visible
3. **Use more specific selector** - Use `getByTestId` or `locator('h1')` instead of role-based
4. **Check loading states** - Ensure test waits for analysis page to finish loading

**Recommended Approach:**
- Add `data-testid="analysis-header"` to `AnalysisHeader` component
- Update test to use `page.getByTestId('analysis-header')` instead of role-based selector
- This is more reliable and doesn't depend on ARIA roles or text matching

---

## Failure #2: Artifact Has No Code Blocks

**Test**: `artifact.spec.ts:44` - "should display code blocks from markdown"  
**Error**:
```
Expected: > 0
Received: 0
```

### Root Cause Analysis

**What the test expects:**
```typescript
const codeBlocks = artifactPage.codeBlocks;
const count = await codeBlocks.count();
expect(count).toBeGreaterThan(0);
```

**What the code actually does:**
```typescript
// frontend/e2e/page-objects/artifact.page.ts:31
this.codeBlocks = page.getByTestId('code-block');
```

**The Problem:**
- The test expects at least 1 code block with `data-testid="code-block"`
- The artifact markdown content **does not contain any code blocks**
- This is a **content issue**, not a rendering issue

**Code Block Rendering:**
- Code blocks ARE properly rendered when they exist:
  - `CodeBlock` component has `data-testid="code-block"` (line 63)
  - `CodeBlock` component has `data-testid="code-block-container"` (line 50)
  - Markdown renderer correctly maps code blocks to `CodeBlock` component (line 64)

**Investigation Needed:**
1. **Check the actual artifact content** - Does the completed analysis artifact contain code blocks?
2. **Verify artifact generation** - Does the backend generate artifacts with code examples?
3. **Check test data** - What artifact is the test using? Is it from the golden dataset?
4. **Verify markdown structure** - Does the artifact markdown have ``` code blocks?

**Code Locations:**
- Test: `frontend/e2e/specs/artifact.spec.ts:44-52`
- Page Object: `frontend/e2e/page-objects/artifact.page.ts:31`
- Component: `frontend/src/features/artifact/components/MarkdownPreview/internal/CodeBlock.tsx:63`
- Renderer: `frontend/src/features/artifact/components/MarkdownPreview/internal/renderers.tsx:64`

**Possible Root Causes:**
1. **Artifact content doesn't have code blocks** - The generated artifact markdown simply doesn't contain code examples
2. **Test is using wrong artifact** - The test might be using an artifact that doesn't have code blocks
3. **Artifact generation issue** - Backend might not be generating code examples in artifacts
4. **Markdown parsing issue** - Code blocks might not be parsed correctly from markdown

**Recommended Approach:**
1. **Check the actual artifact content** - Inspect what artifact the test is using
2. **Verify artifact generation** - Check if backend generates code examples
3. **Update test expectations** - If artifacts don't always have code blocks, make test conditional
4. **Add test data** - Ensure test uses an artifact that definitely has code blocks

**This is likely a test data issue, not a code issue.**

---

## Failure #3: Workflow Stages Not Appearing

**Test**: `full-workflow-13-stages.spec.ts:77` - "should complete full analysis workflow with all 13 stages"  
**Error**:
```
Expected: 6
Received: 0
All 6 core stages must appear
```

### Root Cause Analysis

**What the test expects:**
```typescript
const CORE_STAGES = [
  'extraction',           // Content extraction
  'embedding',            // Embedding generation
  'supervisor_routing',   // Agent selection
  'aggregation',          // Results aggregation
  'quality_validation',   // Quality check
  'artifact_generation',  // Final report generation
];

expect(coreCount, 'All 6 core stages must appear').toBe(CORE_STAGES.length);
```

**What actually happens:**
- Test monitors SSE events for stage names
- **0 out of 6 core stages** are detected
- This means either:
  1. SSE events are not being emitted
  2. SSE events have different stage names
  3. SSE events are not being parsed correctly
  4. Workflow is not running at all

**How the test monitors stages:**
```typescript
// Test monitors SSE endpoint responses
page.on('response', async (response) => {
  if (url.includes('/api/v1/analyze/sse/')) {
    const body = await response.text();
    const lines = body.split('\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.substring(6));
        if (event.stage) {
          stagesEncountered.add(event.stage);
        }
      }
    }
  }
});
```

**Investigation Needed:**
1. **Check SSE event format** - What do actual SSE events look like?
2. **Verify stage names** - Do backend stage names match test expectations?
3. **Check workflow execution** - Is the workflow actually running?
4. **Verify SSE endpoint** - Is the SSE endpoint responding correctly?
5. **Check backend logs** - Are workflow stages being executed?

**Code Locations:**
- Test: `frontend/e2e/specs/full-workflow-13-stages.spec.ts:77-423`
- SSE Monitoring: `frontend/e2e/specs/full-workflow-13-stages.spec.ts:96-130`
- Backend SSE: `backend/app/api/v1/analysis.py` (SSE endpoint)
- Workflow: `backend/app/workflows/` (LangGraph workflow)

**Possible Root Causes:**
1. **Workflow not running** - Backend might be skipping workflow execution
2. **SSE events not emitted** - Backend might not be emitting stage events
3. **Stage name mismatch** - Backend stage names might differ from test expectations
4. **SSE parsing issue** - Test might not be parsing SSE events correctly
5. **Workflow disabled** - `SKILLFORGE_E2E_DISABLE_WORKFLOW` might be set to true
6. **Backend configuration** - Missing API keys or configuration preventing workflow execution

**Recommended Approach:**
1. **Check backend logs** - Verify workflow is actually running
2. **Inspect SSE events** - Capture actual SSE event format
3. **Verify stage names** - Check backend `AGENT_REGISTRY` and stage names
4. **Check configuration** - Verify `SKILLFORGE_E2E_DISABLE_WORKFLOW` is false
5. **Test SSE endpoint directly** - Manually test SSE endpoint to see actual events

**This is likely a backend workflow execution issue, not a frontend issue.**

---

## Summary of Issues

| Test | Category | Root Cause | Severity | Fix Complexity |
|------|----------|------------|----------|----------------|
| Analysis metadata heading | UI Selector | Heading not found via role selector | Low | Easy - Add test ID |
| Artifact code blocks | Content/Data | Artifact doesn't contain code blocks | Medium | Medium - Check test data |
| Workflow stages | Backend Execution | Workflow not emitting SSE events | High | Hard - Backend investigation |

---

## Next Steps

1. **Fix #1 (Heading)** - Add `data-testid` to `AnalysisHeader` and update test
2. **Investigate #2 (Code Blocks)** - Check actual artifact content and test data
3. **Investigate #3 (Workflow)** - Check backend logs, SSE events, and workflow execution

---

## Notes

- All 3 failures are **separate issues** from the navigation/context problems we fixed
- None of these require timeout increases (as per user requirement)
- Each requires different investigation approaches
- Fix #1 is straightforward (add test ID)
- Fixes #2 and #3 require deeper investigation


