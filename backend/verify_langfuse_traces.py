#!/usr/bin/env python3
"""Verify Langfuse traces are being recorded."""

import os
import sys
from datetime import datetime, timedelta, UTC

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.core.langfuse_service import get_langfuse_service


def verify_langfuse_traces() -> None:
    """Verify that Langfuse is receiving traces."""
    service = get_langfuse_service()

    if not service:
        print("❌ Langfuse service not configured!")
        print("\nCheck environment variables:")
        print(f"  LANGFUSE_ENABLED={os.getenv('LANGFUSE_ENABLED')}")
        print(f"  LANGFUSE_PUBLIC_KEY={'SET' if os.getenv('LANGFUSE_PUBLIC_KEY') else 'NOT SET'}")
        print(f"  LANGFUSE_SECRET_KEY={'SET' if os.getenv('LANGFUSE_SECRET_KEY') else 'NOT SET'}")
        print(f"  LANGFUSE_HOST={os.getenv('LANGFUSE_HOST')}")
        sys.exit(1)

    print("✅ Langfuse service configured")
    print(f"   Host: {service.host}")
    print(f"   Public Key: {service.public_key[:20]}...")
    print()

    # Check if SDK client is available
    if not service.sdk_client:
        print("❌ Langfuse SDK client not available!")
        sys.exit(1)

    print("✅ Langfuse SDK client initialized")
    print()

    # Fetch recent traces using the SDK
    print("Fetching recent traces (last 24 hours)...")

    try:
        # Use Langfuse SDK to fetch traces
        # The SDK doesn't have a direct list_traces method, so we'll use the HTTP API
        import httpx

        # Calculate timestamp 24 hours ago
        since = datetime.now(UTC) - timedelta(hours=24)

        # Fetch traces via HTTP API
        url = f"{service.host}/api/public/traces"
        params = {
            "page": 1,
            "limit": 10,
        }

        response = httpx.get(
            url,
            auth=(service.public_key, service.secret_key),
            params=params,
            timeout=10.0,
        )

        if response.status_code == 200:
            data = response.json()
            traces = data.get("data", [])
            total = data.get("meta", {}).get("totalItems", len(traces))

            print(f"✅ Langfuse API accessible")
            print(f"   Total traces: {total}")
            print(f"   Recent traces (page 1): {len(traces)}")
            print()

            if traces:
                print("Recent trace details:")
                for i, trace in enumerate(traces[:5], 1):
                    trace_id = trace.get("id", "unknown")
                    name = trace.get("name", "unnamed")
                    timestamp = trace.get("timestamp", "unknown")

                    print(f"  {i}. ID: {trace_id}")
                    print(f"     Name: {name}")
                    print(f"     Timestamp: {timestamp}")

                    # Check for our analysis ID
                    metadata = trace.get("metadata", {})
                    if metadata:
                        print(f"     Metadata: {metadata}")

                    print()
            else:
                print("⚠️  No traces found in Langfuse!")
                print("\nPossible reasons:")
                print("1. The analysis workflow might not be creating traces")
                print("2. The CallbackHandler might not be properly attached")
                print("3. Traces might not have been flushed yet")
                print("\nTry:")
                print("- Running another analysis")
                print("- Checking if LANGFUSE_ENABLED=true in .env")
                print("- Checking backend logs for Langfuse errors")
        else:
            print(f"❌ Langfuse API returned {response.status_code}")
            print(f"   Response: {response.text[:200]}")

    except Exception as e:
        print(f"❌ Error fetching traces: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    verify_langfuse_traces()
