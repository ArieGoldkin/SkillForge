---
description: Capture web content using browser tools
---

Capture content from: $ARGUMENTS

## Options

### 1. Playwright MCP (Preferred for automation)
Use when you need to capture JavaScript-rendered content, SPAs, or login-protected pages:

```python
mcp__playwright__browser_navigate(url="$ARGUMENTS")
mcp__playwright__browser_snapshot()  # Get accessibility tree (better than screenshot)
# or
mcp__playwright__browser_take_screenshot()  # Visual capture
```

### 2. WebFetch (Simple pages)
For static content that doesn't require JavaScript:
```python
WebFetch(url="$ARGUMENTS", prompt="Extract the main content")
```

### 3. Claude Chrome Extension (User-assisted)
When Playwright can't access (auth-protected, captcha, etc.):
1. Ask user to open URL in Chrome with Claude extension
2. User captures page with extension
3. Content appears in conversation

## Common Use Cases

**Documentation capture**:
```python
mcp__playwright__browser_navigate(url="https://docs.example.com/api")
mcp__playwright__browser_snapshot()
```

**Multi-page docs**:
```python
# Navigate and capture each page
for page in pages:
    mcp__playwright__browser_navigate(url=page)
    mcp__playwright__browser_snapshot(filename=f"docs/{page_name}.md")
```

**Login-required content**:
Ask user to authenticate via Chrome extension, then continue from captured content.

## After Capture
- Analyze content for relevant patterns
- Extract code examples
- Summarize key points
- Save to `.claude/context/` if needed for future reference
