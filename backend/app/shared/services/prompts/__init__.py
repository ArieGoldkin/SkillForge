"""Prompt engineering services.

This module contains advanced prompting techniques:
- Chain-of-Thought (CoT) prompting for complex reasoning tasks
- Langfuse Prompt Management (Issue #379)
"""

from app.shared.services.prompts.chain_of_thought import (
    get_all_cot_agent_types,
    get_cot_prompt,
)
from app.shared.services.prompts.prompt_manager import (
    PromptManager,
    get_prompt_manager,
)

__all__ = [
    "PromptManager",
    "get_all_cot_agent_types",
    "get_cot_prompt",
    "get_prompt_manager",
]
