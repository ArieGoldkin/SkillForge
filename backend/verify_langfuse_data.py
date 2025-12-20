#!/usr/bin/env python3
"""
Verify Langfuse data from recent test runs.

Checks for:
1. Traces in Langfuse
2. G-Eval scores (LLM-as-a-Judge)
3. User feedback scores
"""
import httpx
import os
import sys
from datetime import datetime, timedelta
from collections import Counter

# Langfuse credentials from environment
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "pk-lf-a2a89dc7-fe10-4584-b8d1-28bb47018ae9")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "sk-lf-ac49d63e-cd97-42b7-9a24-6af77a1315fa")

def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def print_section(text: str):
    """Print a formatted section header."""
    print(f"\n{text}")
    print("-" * 80)

def query_langfuse(endpoint: str, params: dict = None) -> dict:
    """Query Langfuse API with authentication."""
    url = f"{LANGFUSE_HOST}/api/public/{endpoint}"

    try:
        response = httpx.get(
            url,
            params=params,
            auth=(LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY),
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        print(f"ERROR querying {endpoint}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        return None

def main():
    print_header("LANGFUSE DATA VERIFICATION REPORT")
    print(f"Langfuse Host: {LANGFUSE_HOST}")
    print(f"Public Key: {LANGFUSE_PUBLIC_KEY[:20]}...")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Query traces
    print_section("1. TRACES")
    traces_data = query_langfuse("traces", params={"page": 1, "limit": 100})

    if traces_data:
        traces = traces_data.get("data", [])
        total_traces = traces_data.get("meta", {}).get("totalItems", 0)
        print(f"Total traces: {total_traces}")
        print(f"Retrieved: {len(traces)} traces")

        if traces:
            # Show recent traces
            print("\nRecent traces (latest 5):")
            for i, trace in enumerate(traces[:5], 1):
                trace_id = trace.get("id")
                name = trace.get("name", "Unnamed")
                timestamp = trace.get("timestamp", "Unknown")
                user_id = trace.get("userId", "N/A")
                metadata = trace.get("metadata", {})

                print(f"\n  {i}. Trace ID: {trace_id}")
                print(f"     Name: {name}")
                print(f"     Timestamp: {timestamp}")
                print(f"     User ID: {user_id}")
                if metadata:
                    print(f"     Metadata: {metadata}")
    else:
        print("Failed to retrieve traces")
        total_traces = 0

    # Query scores
    print_section("2. SCORES")
    scores_data = query_langfuse("scores", params={"page": 1, "limit": 100})

    if scores_data:
        scores = scores_data.get("data", [])
        total_scores = scores_data.get("meta", {}).get("totalItems", 0)
        print(f"Total scores: {total_scores}")
        print(f"Retrieved: {len(scores)} scores")

        if scores:
            # Analyze score types
            score_types = Counter(score.get("name", "Unknown") for score in scores)
            print("\nScore types breakdown:")
            for score_type, count in score_types.most_common():
                print(f"  - {score_type}: {count}")

            # Separate by category
            g_eval_scores = [s for s in scores if "quality_" in s.get("name", "")]
            user_feedback_scores = [s for s in scores if s.get("name", "") == "user_feedback"]

            print(f"\nG-Eval (LLM-as-a-Judge) scores: {len(g_eval_scores)}")
            print(f"User feedback scores: {len(user_feedback_scores)}")

            # Show sample G-Eval scores
            if g_eval_scores:
                print("\nSample G-Eval scores (latest 3):")
                for i, score in enumerate(g_eval_scores[:3], 1):
                    score_id = score.get("id")
                    name = score.get("name")
                    value = score.get("value")
                    trace_id = score.get("traceId")
                    timestamp = score.get("timestamp")
                    comment = score.get("comment", "")

                    print(f"\n  {i}. Score ID: {score_id}")
                    print(f"     Type: {name}")
                    print(f"     Value: {value}")
                    print(f"     Trace ID: {trace_id}")
                    print(f"     Timestamp: {timestamp}")
                    if comment:
                        print(f"     Comment: {comment[:100]}...")

            # Show sample user feedback scores
            if user_feedback_scores:
                print("\nSample User Feedback scores (latest 3):")
                for i, score in enumerate(user_feedback_scores[:3], 1):
                    score_id = score.get("id")
                    name = score.get("name")
                    value = score.get("value")
                    trace_id = score.get("traceId")
                    timestamp = score.get("timestamp")
                    comment = score.get("comment", "")

                    print(f"\n  {i}. Score ID: {score_id}")
                    print(f"     Type: {name}")
                    print(f"     Value: {value}")
                    print(f"     Trace ID: {trace_id}")
                    print(f"     Timestamp: {timestamp}")
                    if comment:
                        print(f"     Comment: {comment[:100]}...")

            # Find a trace with associated scores
            print_section("3. SAMPLE TRACE WITH SCORES")
            trace_score_map = {}
            for score in scores:
                trace_id = score.get("traceId")
                if trace_id:
                    if trace_id not in trace_score_map:
                        trace_score_map[trace_id] = []
                    trace_score_map[trace_id].append(score)

            if trace_score_map:
                # Find trace with most scores
                richest_trace_id = max(trace_score_map.keys(), key=lambda k: len(trace_score_map[k]))
                trace_scores = trace_score_map[richest_trace_id]

                print(f"Trace ID: {richest_trace_id}")
                print(f"Associated scores: {len(trace_scores)}")
                print("\nScore details:")
                for score in trace_scores:
                    name = score.get("name")
                    value = score.get("value")
                    print(f"  - {name}: {value}")
            else:
                print("No traces with associated scores found")
    else:
        print("Failed to retrieve scores")
        total_scores = 0

    # Summary
    print_section("4. SUMMARY")
    print(f"Total Traces: {total_traces}")
    print(f"Total Scores: {total_scores if scores_data else 0}")

    if scores_data and scores:
        g_eval_count = len([s for s in scores if "quality_" in s.get("name", "")])
        user_feedback_count = len([s for s in scores if s.get("name", "") == "user_feedback"])

        print(f"\nScore Breakdown:")
        print(f"  G-Eval (LLM-as-a-Judge): {g_eval_count}")
        print(f"  User Feedback (Human Annotation): {user_feedback_count}")

        print(f"\nData Validation:")
        print(f"  LLM-as-a-Judge data present: {'YES' if g_eval_count > 0 else 'NO'}")
        print(f"  Human Annotation data present: {'YES' if user_feedback_count > 0 else 'NO'}")

    print("\n" + "=" * 80)
    print("Verification complete!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
