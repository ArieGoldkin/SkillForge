---
name: socratic-questioning
description: Socratic method for refining ideas through questions
version: 1.0.0
tags: [brainstorming, socratic, questioning, refinement]
size: atomic
domain: process
---

# Socratic Questioning

## The Method

Refine rough ideas into fully-formed designs through structured questioning.

## Question Categories

### 1. Clarifying Questions

- What do you mean by...?
- Can you give an example?
- How does this relate to...?
- What is the main point?

### 2. Probing Assumptions

- What are you assuming?
- Why do you think that's true?
- What would happen if that's wrong?
- Is that always the case?

### 3. Probing Evidence

- What evidence supports this?
- How do you know?
- Can you give me an example?
- What would change your mind?

### 4. Perspective Questions

- What would X think about this?
- What's the opposite view?
- Who benefits from this?
- Who might disagree?

### 5. Implication Questions

- What are the consequences?
- What does this imply?
- How does this affect...?
- What would happen if...?

### 6. Meta Questions

- Why is this question important?
- What was the point of asking that?
- What does this tell us?
- Where do we go from here?

## Application to Design

```
User: "I want to add caching"

Clarifying:
- What specifically do you want to cache?
- What's the current performance problem?

Assumptions:
- Are you assuming all users need the same cached data?
- What if the data changes frequently?

Evidence:
- What metrics show caching would help?
- What's the current latency?

Implications:
- What happens with cache invalidation?
- How does this affect consistency?

Perspective:
- How would ops manage this cache?
- What about users in different regions?
```

## Best Practices

- ✅ Ask, don't tell
- ✅ Follow the user's train of thought
- ✅ Build on previous answers
- ✅ Surface decisions, don't make them
