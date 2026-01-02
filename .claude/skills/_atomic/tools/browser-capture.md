---
name: browser-capture
description: Playwright MCP for JavaScript-rendered content capture
version: 1.0.0
tags: [browser, playwright, scraping, spa]
size: atomic
domain: tools
---

# Browser Content Capture

## When to Use

- `WebFetch` returns empty/partial content
- Page requires JavaScript to render
- Content is behind authentication
- Need to navigate multi-page structures

## MCP Tools Reference

| Tool | Purpose |
|------|---------|
| `browser_navigate` | Go to URL |
| `browser_snapshot` | Get DOM tree |
| `browser_evaluate` | Run custom JS |
| `browser_click` | Click elements |
| `browser_fill_form` | Fill inputs |
| `browser_wait_for` | Wait for selector |

## Basic Pattern

```python
# 1. Navigate
mcp__playwright__browser_navigate(url="https://docs.example.com")

# 2. Wait for content
mcp__playwright__browser_wait_for(selector=".main-content", timeout=5000)

# 3. Capture snapshot
snapshot = mcp__playwright__browser_snapshot()

# 4. Extract text
content = mcp__playwright__browser_evaluate(
    script="document.querySelector('.main-content').innerText"
)
```

## SPA Extraction

```python
# Navigate and wait for hydration
mcp__playwright__browser_navigate(url="https://react-app.com")
mcp__playwright__browser_wait_for(selector="[data-hydrated='true']")

# Extract after React mounts
content = mcp__playwright__browser_evaluate(script="""
    await new Promise(r => setTimeout(r, 1000));
    return document.querySelector('article').innerText;
""")
```

## Authentication

```python
# Navigate to login
mcp__playwright__browser_navigate(url="https://example.com/login")

# Fill credentials
mcp__playwright__browser_fill_form(
    selector="#login-form",
    values={"username": "...", "password": "..."}
)

# Click submit
mcp__playwright__browser_click(selector="button[type='submit']")
mcp__playwright__browser_wait_for(selector=".dashboard")
```

## Decision Tree

```
Try WebFetch first (faster)
        │
   Content OK? ──Yes──▶ Done
        │
        No
        │
   Known SPA? ──▶ Playwright MCP
   Login required? ──▶ Chrome Extension
   Dynamic content? ──▶ Playwright + wait_for
```
