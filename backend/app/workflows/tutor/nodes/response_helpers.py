"""Helper functions for processing LLM responses in tutor workflow nodes."""

from typing import Any


def extract_string_content(response: Any) -> str:
    """Extract string content from LLM response.

    LLM responses can have content as:
    - str: Direct string content
    - list[str | dict[Any, Any]]: List of content chunks (from streaming)
    - dict: Structured response

    This function safely extracts a string representation.

    Args:
        response: LLM response object (AIMessage or similar)

    Returns:
        String content from the response

    """
    if not hasattr(response, "content"):
        return str(response)

    content = response.content

    # If content is already a string, return it
    if isinstance(content, str):
        return content

    # If content is a list, join string elements
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                # Try to extract text from dict
                if "text" in item:
                    parts.append(str(item["text"]))
                elif "content" in item:
                    parts.append(str(item["content"]))
                else:
                    parts.append(str(item))
        return "".join(parts)

    # If content is a dict, try to extract text
    if isinstance(content, dict):
        if "text" in content:
            return str(content["text"])
        if "content" in content:
            return str(content["content"])
        return str(content)

    # Fallback: convert to string
    return str(content)
