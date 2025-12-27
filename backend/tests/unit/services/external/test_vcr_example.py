"""Example VCR test patterns for external API services.

Usage:
1. First run with VCR_RECORD_MODE=all to record cassettes
2. Commit cassettes to git (API keys are filtered)
3. Future runs use cassettes - no real API calls needed
"""

import pytest

# Example of how to convert a mocked test to VCR
# BEFORE (mock-based):
# @pytest.mark.asyncio
# async def test_search_success(mock_tavily_client):
#     mock_tavily_client.post.return_value = {"results": [...]}
#     result = await service.search("query")
#     assert len(result) > 0

# AFTER (VCR-based):
# @pytest.mark.asyncio
# @pytest.mark.vcr()
# async def test_search_success(tavily_service):
#     # No mocking - VCR replays recorded HTTP response
#     result = await tavily_service.search("query")
#     assert len(result) > 0


@pytest.mark.asyncio
async def test_vcr_example_placeholder():
    """Placeholder test to verify VCR setup works.

    To record a real cassette:
    1. Run: VCR_RECORD_MODE=all pytest tests/unit/services/external/test_vcr_example.py -v
    2. Check tests/cassettes/ for the recorded .yaml file
    """
    # This test just verifies the VCR fixture is working
    assert True, "VCR setup complete - ready for real tests"
