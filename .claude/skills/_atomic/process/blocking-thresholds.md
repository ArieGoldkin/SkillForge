---
name: blocking-thresholds
description: Quality gate blocking conditions and escalation
version: 1.0.0
tags: [quality-gates, blocking, escalation, workflow]
size: atomic
domain: process
---

# Blocking Thresholds

## BLOCKING Conditions (Must Resolve)

### 1. Incomplete Requirements

> **>3 critical questions unanswered → BLOCK**

Critical questions examples:
- "What should happen when X fails?"
- "What data structure should I use?"
- "Which API should I call?"
- "What authentication method?"

### 2. Missing Dependencies

- Task depends on incomplete work
- Required API endpoint doesn't exist
- Database schema not ready
- External service not configured

### 3. Stuck Detection

> **3+ failed attempts → BLOCK & ESCALATE**

Track every attempt:
- Attempt 1: [Approach] → [Outcome]
- Attempt 2: [Approach] → [Outcome]
- Attempt 3: [Approach] → [Outcome]

### 4. Evidence Failure

- Tests fail after 2 fix attempts
- Build breaks after changes
- Type errors persist
- Integration tests failing

### 5. Complexity Overflow

> **Level 4-5 without breakdown → BLOCK**

Complex tasks must be broken into Level 1-3 subtasks first.

## WARNING Conditions (Proceed with Caution)

- Level 3 complexity → Document assumptions
- 1-2 unanswered questions → Proceed with best guess
- 1-2 failed attempts → Try alternative approach

## Gate Decision Flow

```
1. Assess complexity (1-5)
2. Count critical questions unanswered
3. Check dependencies blocked
4. Check attempt count

if (questions > 3) → BLOCK
if (dependencies blocked) → BLOCK
if (attempts >= 3) → BLOCK & ESCALATE
if (complexity >= 4 && no plan) → BLOCK
if (complexity == 3) → WARNING
else → PASS
```

## Escalation Template

```markdown
## 🚨 Task Stuck

**Task:** [Description]
**Attempts:** 3
**Status:** BLOCKED

### What Was Tried
1. Attempt 1: [Approach] → Failed: [Reason]
2. Attempt 2: [Approach] → Failed: [Reason]
3. Attempt 3: [Approach] → Failed: [Reason]

### Need Guidance On
- [Specific question 1]
- [Specific question 2]
```
