"""Timeout configuration constants for agent execution.

This module centralizes all timeout values used throughout the application
to improve maintainability and consistency.
"""

# Agent execution timeout (in seconds)
AGENT_TIMEOUT: float = 120.0  # 120 seconds (2 minutes) max per agent for complex LLM calls

# LLM synthesis timeout (in seconds)
SYNTHESIS_TIMEOUT: float = 120.0  # 120 seconds for aggregation synthesis

# Streaming timeout (in seconds)
STREAMING_TIMEOUT: float = 300.0  # 300 seconds (5 minutes) for long-running streams
