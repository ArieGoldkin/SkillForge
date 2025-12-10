"""MCP Integration Tests.

This package contains integration tests for the MCP (Model Context Protocol)
system, validating end-to-end flows from agent runners through the tool
registry to the MCP client pool.

Test Categories:
- Pool lifecycle: Connection state transitions, tool caching
- Registry integration: Tool filtering by agent capabilities
- Agent end-to-end: Full flow with mocked MCP servers
- Resilience: Graceful degradation, circuit breaker, retry logic
"""
