"""Prompt engineering services.

This module contains advanced prompting techniques:
- Chain-of-Thought (CoT) prompting for complex reasoning tasks
"""

from app.shared.services.prompts.chain_of_thought import (
    get_all_cot_agent_types,
    get_cot_prompt,
)

__all__ = ["get_all_cot_agent_types", "get_cot_prompt"]
