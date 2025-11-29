#!/usr/bin/env python3
"""Manual test script to verify LangSmith tracing is working."""

import os
import time

from langsmith import traceable

# Check environment
print("=== LangSmith Tracing Test ===")
print(f"LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2')}")
print(f"LANGSMITH_TRACING: {os.getenv('LANGSMITH_TRACING')}")
print(f"LANGCHAIN_PROJECT: {os.getenv('LANGCHAIN_PROJECT')}")
print(f"LANGSMITH_API_KEY set: {'YES' if os.getenv('LANGSMITH_API_KEY') else 'NO'}")

if os.getenv("LANGSMITH_API_KEY"):
    print(f"API key length: {len(os.getenv('LANGSMITH_API_KEY'))}")


@traceable(name="test_function")
def test_function(input_text: str) -> str:
    """Test function that should be traced."""
    print(f"Processing: {input_text}")
    time.sleep(1)  # Simulate work
    return f"Processed: {input_text}"


if __name__ == "__main__":
    print("\nCalling test function...")
    result = test_function("Hello LangSmith!")
    print(f"Result: {result}")

    print("\nWaiting 5 seconds for traces to send...")
    time.sleep(5)

    print("Test complete. Check LangSmith dashboard for traces.")
