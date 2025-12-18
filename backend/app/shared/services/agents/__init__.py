"""Agent services for Few-Shot Prompting and agent creation.

This module provides factory functions and utilities for creating agents
with enhanced capabilities like few-shot example injection.
"""

from app.shared.services.agents.few_shot_factory import create_few_shot_agent

__all__ = [
    "create_few_shot_agent",
]
