# Freshness Checker Agent Implementation

## Overview

Implemented the `freshness_checker` agent as a Tier 2 Validation agent that analyzes technical content for version currency by:
1. Extracting version references from content (e.g., "React 18.2", "Python 3.11")
2. Checking against npm/PyPI APIs via MCP tools for latest versions
3. Flagging outdated content with specific version gap analysis

## Files Created/Modified

### New Files
1. **`/Users/yonatangross/coding/SkillForge/backend/app/domains/analysis/workflows/agents/freshness_checker.py`**
   - Main agent implementation following established Tier 1 agent patterns
   - Integrates with PromptManager for Langfuse prompt fetching (Issue #418)
   - Uses MCP tools (npm, PyPI) for version checking
   - Implements grounding, skill level adaptation, and content-aware specificity thresholds

2. **`/Users/yonatangross/coding/SkillForge/backend/tests/unit/domains/analysis/workflows/agents/test_freshness_checker.py`**
   - Comprehensive test suite with 6 test cases
   - Tests basic functionality (current/outdated versions)
   - Tests MCP tool integration
   - Tests edge cases (no versions found, registry unavailable)
   - Tests PromptManager integration
   - All tests passing

### Modified Files

1. **`/Users/yonatangross/coding/SkillForge/backend/app/shared/services/mcp/registry.py`**
   - Added `freshness_checker` to `AGENT_TOOL_CONFIGS`
   - Configured with npm and PyPI tool capabilities
   - Set max_tool_calls=15, tool_timeout=25.0
   - Includes standard ARTIFACT_LOAD and MEMORY_SEARCH capabilities

2. **`/Users/yonatangross/coding/SkillForge/backend/app/domains/analysis/workflows/agents/factories.py`**
   - Added `create_freshness_checker_agent_with_few_shot()` factory function
   - Follows same pattern as other Tier 2 agents (fact_validator, alternatives_finder)
   - Configures ToolCallConfig with max_tool_calls=15

3. **`/Users/yonatangross/coding/SkillForge/backend/app/shared/services/prompts/prompt_manager.py`**
   - Added hardcoded fallback prompt for "analysis-agent-freshness-checker"
   - Provides comprehensive field requirements and examples
   - Includes tool usage guidelines for npm/PyPI APIs

## Schema

The agent uses the existing `FreshnessCheckerOutput` schema from `/Users/yonatangross/coding/SkillForge/backend/app/domains/analysis/schemas/agents/freshness_checker.py`:

```python
class VersionCheck(BaseModel):
    package_name: str
    mentioned_version: str
    latest_version: str
    is_outdated: bool
    versions_behind: int
    ecosystem: str  # npm, pypi, language, framework, other

class FreshnessCheckerOutput(DataAvailabilityMixin):
    content_date: str | None
    version_checks: list[VersionCheck]
    is_outdated: bool
    freshness_score: float  # 0.0-1.0
    recommendations: list[str]
    confidence_score: float  # 0.0-1.0
```

## Key Features

### 1. MCP Tool Integration
- Uses `get-npm-package-details` for JavaScript packages
- Uses `get-pypi-package-details` for Python packages
- Handles tool failures gracefully (sets latest_version="unknown")
- Maximum 15 tool calls per analysis

### 2. Version Extraction
- Extracts semantic versions (major.minor.patch)
- Handles version range specifiers (^, ~, >=)
- Identifies language versions (Python, Node.js, Java)
- Normalizes versions for comparison

### 3. Freshness Scoring
- 1.0: All versions current, content <6 months old
- 0.8-0.9: 1-2 minor versions behind, 6-12 months old
- 0.6-0.7: 1 major version behind OR 12-18 months old
- 0.4-0.5: Multiple major versions behind OR 18-24 months old
- 0.0-0.3: Severely outdated (3+ major behind OR >2 years old)

### 4. Recommendations
- Specific package upgrade suggestions
- Includes rationale (features, security, performance)
- Prioritizes security-critical updates
- Empty list if content is fresh (score >= 0.9)

## Agent Prompt

The agent prompt includes:
- Clear mission statement and field requirements
- Version extraction patterns and guidelines
- Tool usage guidelines for npm/PyPI APIs
- Ecosystem classification (npm, pypi, language, framework, other)
- Versions-behind calculation logic
- Date extraction patterns
- Good/bad examples
- Content-type specific guidance

## Testing Results

```bash
poetry run pytest tests/unit/domains/analysis/workflows/agents/test_freshness_checker.py -v
```

**Result: 6 passed in 7.90s**

Test Coverage:
- ✅ Basic freshness checking with current versions
- ✅ Basic freshness checking with outdated versions
- ✅ MCP tool integration
- ✅ Edge case: no versions found
- ✅ Edge case: registry unavailable
- ✅ PromptManager integration

## Quality Checks

All code quality checks passed:

```bash
poetry run ruff format --check  # ✅ All formatted
poetry run ruff check           # ✅ All checks passed
poetry run ty check            # ✅ Type checks passed
```

## Integration Points

### 1. Workflow Integration
The agent follows the same execution pattern as other Tier 1 agents:
- Uses `run_agent_with_tracking()` for consistent execution
- Emits SSE events for progress tracking
- Records results to `agent_findings` table
- Supports skill level adaptation
- Implements content-aware specificity thresholds

### 2. MCP Tool Flow
```
Content → Extract versions → Call npm/pypi tools → Compare versions →
Calculate freshness score → Generate recommendations → Return findings
```

### 3. Fallback Behavior
- Primary: Fetch prompt from Langfuse
- Fallback: Use hardcoded prompt from PromptManager
- Tool failure: Set latest_version="unknown", note in confidence score

## Example Usage

```python
from app.domains.analysis.workflows.agents.freshness_checker import run_freshness_checker

result = await run_freshness_checker(
    content="React 18.2.0 Tutorial from 2023...",
    content_type="article",
    analysis_id=analysis_id,
    session=session,
    state=state,
    tools=mcp_tools,  # npm + PyPI tools
)

# Result:
# {
#   "agent_type": "freshness_checker",
#   "findings": {
#     "content_date": "2023-06-01",
#     "version_checks": [
#       {
#         "package_name": "react",
#         "mentioned_version": "18.2.0",
#         "latest_version": "19.0.0",
#         "is_outdated": true,
#         "versions_behind": 1,
#         "ecosystem": "npm"
#       }
#     ],
#     "is_outdated": true,
#     "freshness_score": 0.7,
#     "recommendations": [
#       "Update React from 18.2.0 to 19.0.0 for concurrent features"
#     ],
#     "confidence_score": 0.85
#   },
#   "processing_time_ms": 2500
# }
```

## Next Steps

The agent is now ready for:
1. Integration into the analysis workflow routing logic
2. End-to-end testing with real MCP tools
3. Langfuse prompt creation for production use
4. Performance monitoring and optimization

## Compliance

- ✅ Follows Tier 1 agent pattern established in Issue #499
- ✅ Uses PromptManager (Issue #418)
- ✅ Implements grounding and skill level adaptation
- ✅ Includes MCP tool integration (Issue #436)
- ✅ All tests passing (6/6)
- ✅ All linting checks passed
- ✅ Type checking passed
- ✅ Documentation complete
