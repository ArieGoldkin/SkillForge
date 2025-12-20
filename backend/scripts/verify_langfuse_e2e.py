"""End-to-end verification script for Langfuse integration.

This script:
1. Creates a new analysis via the API
2. Waits for completion (with timeout)
3. Queries Langfuse for traces and spans
4. Reports on agent spans and g_eval scores
"""

import asyncio
import os
import sys
import time
from datetime import datetime, timezone

import httpx

# Configuration
BACKEND_URL = "http://localhost:8500"
LANGFUSE_HOST = "http://localhost:3000"
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "pk-lf-59614692-92e1-4d9a-bcca-d20bd37b10bf")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "sk-lf-cd0fd228-78d6-4ee1-a175-1a9569c2a38a")

# Test URL - simple Python docs page
TEST_URL = "https://docs.python.org/3/tutorial/index.html"

# Timeout for analysis completion (5 minutes)
COMPLETION_TIMEOUT = 300


async def create_analysis(client: httpx.AsyncClient) -> str:
    """Create a new analysis and return the analysis_id."""
    print(f"\n1. Creating analysis for URL: {TEST_URL}")

    response = await client.post(
        f"{BACKEND_URL}/api/v1/analyze",
        json={"url": TEST_URL}
    )

    if response.status_code != 201:
        print(f"ERROR: Failed to create analysis: {response.status_code}")
        print(response.text)
        sys.exit(1)

    data = response.json()
    analysis_id = data["analysis_id"]

    print(f"   ✓ Analysis created: {analysis_id}")
    print(f"   ✓ Content type: {data['content_type']}")
    print(f"   ✓ SSE endpoint: {data['sse_endpoint']}")

    return analysis_id


async def wait_for_completion(client: httpx.AsyncClient, analysis_id: str) -> dict:
    """Poll the analysis status endpoint until completion or timeout."""
    print(f"\n2. Waiting for analysis to complete (timeout: {COMPLETION_TIMEOUT}s)...")

    start_time = time.time()
    last_status = None

    while True:
        elapsed = time.time() - start_time

        if elapsed > COMPLETION_TIMEOUT:
            print(f"   ✗ TIMEOUT after {COMPLETION_TIMEOUT}s")
            print(f"   Last status: {last_status}")
            break

        response = await client.get(f"{BACKEND_URL}/api/v1/analyze/{analysis_id}")

        if response.status_code != 200:
            print(f"   ✗ Failed to get status: {response.status_code}")
            await asyncio.sleep(5)
            continue

        data = response.json()
        status = data["status"]

        if status != last_status:
            print(f"   [{int(elapsed)}s] Status: {status}")
            last_status = status

        if status in ["completed", "complete", "failed", "error"]:
            print(f"   ✓ Analysis finished with status: {status}")
            return data

        await asyncio.sleep(5)

    # Return partial data if we timed out
    return {"analysis_id": analysis_id, "status": last_status or "unknown"}


async def check_langfuse_traces(analysis_id: str) -> dict:
    """Query Langfuse HTTP API for traces related to this analysis."""
    print(f"\n3. Checking Langfuse for traces (analysis_id: {analysis_id})...")

    # Use HTTP Basic Auth with public_key:secret_key
    import base64
    credentials = f"{LANGFUSE_PUBLIC_KEY}:{LANGFUSE_SECRET_KEY}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get recent traces
        print("   Fetching traces via HTTP API...")
        try:
            response = await client.get(
                f"{LANGFUSE_HOST}/api/public/traces",
                headers=headers,
                params={"limit": 100}
            )

            if response.status_code != 200:
                print(f"   ✗ Failed to fetch traces: {response.status_code}")
                print(f"   Response: {response.text}")
                return {
                    "total_traces": 0,
                    "analysis_traces": 0,
                    "agent_spans": [],
                    "scores": [],
                }

            traces_data = response.json()
            traces = traces_data.get("data", [])
            total_traces = len(traces)

            print(f"   ✓ Found {total_traces} total traces in Langfuse")

            # Filter traces for this analysis
            analysis_traces = [
                t for t in traces
                if t.get("metadata") and t["metadata"].get("analysis_id") == analysis_id
            ]

            print(f"   ✓ Found {len(analysis_traces)} traces for analysis_id={analysis_id}")

            if not analysis_traces:
                print("   ⚠ No traces found for this analysis")
                return {
                    "total_traces": total_traces,
                    "analysis_traces": 0,
                    "agent_spans": [],
                    "scores": [],
                }

            # Examine each trace
            agent_spans = []
            scores = []

            for trace in analysis_traces:
                trace_id = trace.get("id")
                print(f"\n   Trace: {trace_id}")
                print(f"     - Name: {trace.get('name')}")
                print(f"     - Timestamp: {trace.get('timestamp')}")

                # Fetch observations (spans) for this trace
                obs_response = await client.get(
                    f"{LANGFUSE_HOST}/api/public/observations",
                    headers=headers,
                    params={"traceId": trace_id, "limit": 100}
                )

                if obs_response.status_code == 200:
                    observations = obs_response.json().get("data", [])

                    for obs in observations:
                        obs_name = obs.get("name", "")
                        obs_type = obs.get("type", "")
                        print(f"     - Observation: {obs_name} (type: {obs_type})")

                        # Check if this is an agent span
                        if "agent" in obs_name.lower() or "node" in obs_name.lower():
                            agent_spans.append({
                                "name": obs_name,
                                "type": obs_type,
                                "trace_id": trace_id,
                            })

                # Fetch scores for this trace
                scores_response = await client.get(
                    f"{LANGFUSE_HOST}/api/public/scores",
                    headers=headers,
                    params={"traceId": trace_id, "limit": 100}
                )

                if scores_response.status_code == 200:
                    trace_scores = scores_response.json().get("data", [])

                    for score in trace_scores:
                        score_name = score.get("name", "")
                        score_value = score.get("value")
                        print(f"     - Score: {score_name} = {score_value}")
                        scores.append({
                            "name": score_name,
                            "value": score_value,
                            "trace_id": trace_id,
                        })

            return {
                "total_traces": total_traces,
                "analysis_traces": len(analysis_traces),
                "agent_spans": agent_spans,
                "scores": scores,
            }

        except Exception as e:
            print(f"   ✗ Error querying Langfuse: {e}")
            import traceback
            traceback.print_exc()
            return {
                "total_traces": 0,
                "analysis_traces": 0,
                "agent_spans": [],
                "scores": [],
            }


def print_summary(analysis_id: str, analysis_data: dict, langfuse_data: dict):
    """Print a summary report."""
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)

    print(f"\nAnalysis ID: {analysis_id}")
    print(f"Status: {analysis_data.get('status', 'unknown')}")
    print(f"URL: {TEST_URL}")

    if analysis_data.get("artifact_id"):
        print(f"Artifact ID: {analysis_data['artifact_id']}")

    print(f"\nLangfuse Traces:")
    print(f"  - Total traces in system: {langfuse_data['total_traces']}")
    print(f"  - Traces for this analysis: {langfuse_data['analysis_traces']}")
    print(f"  - Agent spans found: {len(langfuse_data['agent_spans'])}")
    print(f"  - Scores submitted: {len(langfuse_data['scores'])}")

    if langfuse_data['agent_spans']:
        print(f"\nAgent Spans ({len(langfuse_data['agent_spans'])}):")
        for span in langfuse_data['agent_spans']:
            print(f"  ✓ {span['name']} (type: {span['type']})")
    else:
        print("\n⚠ No agent spans found in Langfuse")

    if langfuse_data['scores']:
        print(f"\nScores ({len(langfuse_data['scores'])}):")
        for score in langfuse_data['scores']:
            print(f"  ✓ {score['name']} = {score['value']}")
    else:
        print("\n⚠ No scores found in Langfuse")

    print("\n" + "="*80)

    # Determine success
    success = (
        analysis_data.get('status') in ['completed', 'complete'] and
        langfuse_data['analysis_traces'] > 0 and
        len(langfuse_data['agent_spans']) > 0
    )

    if success:
        print("✓ VERIFICATION PASSED")
    else:
        print("✗ VERIFICATION FAILED")

    print("="*80)

    return success


async def main():
    """Run the end-to-end verification."""
    print("="*80)
    print("LANGFUSE E2E VERIFICATION")
    print("="*80)
    print(f"Backend: {BACKEND_URL}")
    print(f"Langfuse: {LANGFUSE_HOST}")
    print(f"Test URL: {TEST_URL}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Create analysis
        analysis_id = await create_analysis(client)

        # Step 2: Wait for completion
        analysis_data = await wait_for_completion(client, analysis_id)

        # Give Langfuse a moment to process the traces
        print("\n   Waiting 5s for Langfuse to process traces...")
        await asyncio.sleep(5)

    # Step 3: Check Langfuse
    langfuse_data = await check_langfuse_traces(analysis_id)

    # Step 4: Print summary
    success = print_summary(analysis_id, analysis_data, langfuse_data)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
