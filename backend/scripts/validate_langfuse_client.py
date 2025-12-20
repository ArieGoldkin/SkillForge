#!/usr/bin/env python3
"""Validate LangfuseClient against real Langfuse instance.

Run from backend directory:
    poetry run python scripts/validate_langfuse_client.py
"""

import asyncio
import os
import sys

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.langfuse_client import LangfuseClient, get_langfuse_api_client


async def main() -> None:
    """Run validation tests."""
    print("=" * 60)
    print("LangfuseClient Validation")
    print("=" * 60)

    # Check environment
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")

    print(f"\nHost: {host}")
    print(f"Public Key: {public_key[:20]}..." if public_key else "Public Key: NOT SET")
    print(f"Secret Key: {secret_key[:20]}..." if secret_key else "Secret Key: NOT SET")

    if not public_key or not secret_key:
        print("\n[ERROR] Missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY")
        print("Set these in your environment or .env file")
        sys.exit(1)

    # Create client
    print("\n" + "-" * 40)
    print("1. Creating LangfuseClient...")
    client = LangfuseClient(
        public_key=public_key,
        secret_key=secret_key,
        host=host,
    )
    print(f"   Circuit breaker state: {client.circuit_state.value}")

    # Test: Get prompts
    print("\n" + "-" * 40)
    print("2. Testing get_prompt()...")
    try:
        prompt = await client.get_prompt("default-analyzer-v1")
        if prompt:
            print(f"   SUCCESS: Got prompt 'default-analyzer-v1'")
            print(f"   Version: {prompt.get('version', 'N/A')}")
        else:
            print("   WARNING: Prompt not found (may not exist yet)")
    except Exception as e:
        print(f"   ERROR: {e}")

    # Test: List datasets
    print("\n" + "-" * 40)
    print("3. Testing get_dataset()...")
    try:
        dataset = await client.get_dataset("golden-dataset")
        if dataset:
            print(f"   SUCCESS: Got dataset 'golden-dataset'")
            print(f"   ID: {dataset.get('id', 'N/A')}")
        else:
            print("   WARNING: Dataset not found (may not exist yet)")
    except Exception as e:
        print(f"   ERROR: {e}")

    # Test: Check annotation queue
    print("\n" + "-" * 40)
    print("4. Testing add_to_annotation_queue()...")
    queue_id = os.getenv("LANGFUSE_ANNOTATION_QUEUE_ID", "")
    if queue_id:
        print(f"   Queue ID: {queue_id}")
        try:
            # Use a test trace ID
            result = await client.add_to_annotation_queue(
                queue_id=queue_id,
                trace_id="test-trace-validation-" + str(asyncio.get_event_loop().time()),
            )
            print(f"   SUCCESS: Added to annotation queue")
        except Exception as e:
            print(f"   ERROR: {e}")
    else:
        print("   SKIPPED: No LANGFUSE_ANNOTATION_QUEUE_ID set")

    # Test: Circuit breaker status
    print("\n" + "-" * 40)
    print("5. Circuit Breaker Status:")
    print(f"   State: {client.circuit_state.value}")
    print(f"   Failure count: {client._circuit_breaker.failure_count}")

    # Cleanup
    print("\n" + "-" * 40)
    print("6. Closing client...")
    await client.close()
    print("   Done")

    print("\n" + "=" * 60)
    print("Validation Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
