#!/usr/bin/env python3
"""Submit real analysis requests to the dev API to verify Sprint 3 features."""
import asyncio

import httpx

API_BASE = "http://127.0.0.1:8000/api/v1"


async def submit_analysis(url: str, description: str):
    """Submit an analysis request and wait for completion."""
    print(f"\n{'='*80}")
    print(f"Submitting: {description}")
    print(f"URL: {url}")
    print(f"{'='*80}\n")

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Submit analysis
        response = await client.post(
            f"{API_BASE}/analyze",
            json={"url": url}
        )
        response.raise_for_status()
        data = response.json()
        analysis_id = data["analysis_id"]

        print(f"✓ Analysis submitted: {analysis_id}")
        print(f"✓ Status: {data['status']}")

        # Poll for completion
        max_attempts = 60
        for attempt in range(max_attempts):
            await asyncio.sleep(2)

            status_response = await client.get(f"{API_BASE}/analyses/{analysis_id}")
            status_data = status_response.json()

            print(f"  [{attempt+1}/{max_attempts}] Status: {status_data['status']}")

            if status_data["status"] == "complete":
                print("\n✅ Analysis complete!")

                # Get the detailed results
                if "supervisor_decision" in status_data:
                    agents = status_data["supervisor_decision"].get("agents", [])
                    reasoning = status_data["supervisor_decision"].get("reasoning", "")

                    print(f"\n📊 Selected Agents: {agents}")
                    print(f"\n💭 Reasoning: {reasoning}")

                    # Check for auto-activations
                    auto_activated = []
                    if "performance_analyst" in agents and "perf" in reasoning.lower():
                        auto_activated.append("performance_analyst")
                    if "security_auditor" in agents and "security" in reasoning.lower():
                        auto_activated.append("security_auditor")
                    if "tech_comparator" in agents and "comparison" in reasoning.lower():
                        auto_activated.append("tech_comparator")
                    if "dependency_mapper" in agents and ("code patterns" in reasoning.lower() or "auto-activ" in reasoning.lower()):
                        auto_activated.append("dependency_mapper")

                    if auto_activated:
                        print(f"\n✨ Auto-activated agents: {auto_activated}")

                return status_data

            elif status_data["status"] == "failed":
                print("\n❌ Analysis failed!")
                print(f"Error: {status_data.get('error', 'Unknown error')}")
                return None

        print("\n⏱️  Timeout waiting for analysis")
        return None


async def main():
    """Run verification tests."""
    print("\n" + "="*80)
    print("SPRINT 3 DEV ENVIRONMENT VERIFICATION")
    print("Testing real API requests with real content")
    print("="*80)

    # Test 1: Performance-focused content
    await submit_analysis(
        url="https://fastapi.tiangolo.com/",
        description="FastAPI docs (should trigger performance_analyst)"
    )

    # Test 2: Security-focused content
    await submit_analysis(
        url="https://www.passlib.us/",
        description="Passlib docs (should trigger security_auditor)"
    )

    print("\n" + "="*80)
    print("VERIFICATION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
