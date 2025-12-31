---
description: LLM caching strategies
---
Implement multi-level caching patterns from SkillForge:

Levels:
1. **Semantic Cache**: Redis with vector similarity (70-85% hit rate)
2. **Prompt Cache**: Claude native caching (95%+ hit rate)
3. **Response Cache**: Cache LLM responses for repeated queries

Tools to use:
- Semantic cache: Vector database embeddings
- Prompt cache: Claude's automatic caching
- Response cache: Redis with LRU eviction

Cost reduction: 70-95% reduction in token usage.
