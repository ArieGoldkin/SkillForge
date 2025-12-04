"""Unit tests for supervisor configuration."""

from app.core.agent_config import AGENT_REGISTRY
from app.workflows.nodes.supervisor_config import (
    SUPERVISOR_PROMPT,
    WORKFLOW_STAGES,
    build_supervisor_prompt,
)


class TestBuildSupervisorPrompt:
    """Test build_supervisor_prompt function."""

    def test_build_supervisor_prompt_contains_all_analysis_agents(self):
        """Test prompt contains all analysis agents from registry."""
        prompt = build_supervisor_prompt()

        # Get analysis agents (exclude workflow stages)
        analysis_agents = [
            config for config in AGENT_REGISTRY.values() if config.agent_type not in WORKFLOW_STAGES
        ]

        # Verify all analysis agents are in prompt
        for agent_config in analysis_agents:
            assert agent_config.agent_type in prompt
            assert agent_config.description in prompt

    def test_build_supervisor_prompt_excludes_workflow_stages(self):
        """Test prompt excludes workflow stage agents."""
        prompt = build_supervisor_prompt()

        # Verify workflow stages are NOT in prompt
        for stage in WORKFLOW_STAGES:
            # Stage names might appear in examples, but agent_type shouldn't be listed
            # Check that it's not in the "Agents:" section
            agents_section = prompt.split("Agents:")[1].split("Examples:")[0]
            assert stage not in agents_section, (
                f"Workflow stage {stage} should not be in agents list"
            )

    def test_build_supervisor_prompt_has_correct_structure(self):
        """Test prompt has correct structure."""
        prompt = build_supervisor_prompt()

        assert "Analyze content and select relevant agents" in prompt
        assert "Output JSON" in prompt
        assert "Agents:" in prompt
        assert "Select based on:" in prompt
        assert "Examples:" in prompt

    def test_build_supervisor_prompt_is_consistent(self):
        """Test that prompt building returns consistent results."""
        prompt1 = build_supervisor_prompt()
        prompt2 = build_supervisor_prompt()

        # Should be same string (consistent results from same registry)
        assert prompt1 == prompt2
        assert len(prompt1) == len(prompt2)

    def test_supervisor_prompt_constant(self):
        """Test SUPERVISOR_PROMPT constant is set correctly."""
        assert SUPERVISOR_PROMPT is not None
        assert len(SUPERVISOR_PROMPT) > 0
        assert isinstance(SUPERVISOR_PROMPT, str)

    def test_supervisor_prompt_matches_build_function(self):
        """Test SUPERVISOR_PROMPT matches build_supervisor_prompt()."""
        built_prompt = build_supervisor_prompt()
        assert built_prompt == SUPERVISOR_PROMPT

    def test_supervisor_prompt_agent_list_format(self):
        """Test agent list in prompt has correct format."""
        prompt = build_supervisor_prompt()
        # Agent list is between "Agents:" and "AGENT SELECTION GUIDELINES:"
        agents_section = prompt.split("Agents:")[1].split("AGENT SELECTION GUIDELINES:")[0]

        # Should have format: "- agent_type: description"
        lines = [line.strip() for line in agents_section.split("\n") if line.strip()]
        for line in lines:
            assert line.startswith("- "), f"Agent line should start with '- ': {line}"
            assert ": " in line, f"Agent line should have ': ': {line}"

    def test_supervisor_prompt_contains_examples(self):
        """Test prompt contains example agent selections."""
        prompt = build_supervisor_prompt()

        assert "React tutorial" in prompt or "Quick tip" in prompt
        assert "Security guide" in prompt or "Security deep-dive" in prompt
        assert "API comparison" in prompt or "Architecture comparison" in prompt
        assert "implementation_planner" in prompt or "code_quality_critic" in prompt
        assert "security_auditor" in prompt or "trend_validator" in prompt
        assert "tech_comparator" in prompt or "performance_analyst" in prompt

    def test_supervisor_prompt_contains_guidelines(self):
        """Test prompt contains agent selection guidelines."""
        prompt = build_supervisor_prompt()

        assert "AGENT SELECTION GUIDELINES" in prompt
        assert "SHORT content" in prompt
        assert "MEDIUM content" in prompt
        assert "COMPREHENSIVE content" in prompt
        assert "<1000 words" in prompt or "1000 words" in prompt
        assert "3000 words" in prompt or ">3000 words" in prompt

    def test_supervisor_prompt_contains_content_triggers(self):
        """Test prompt contains content type triggers."""
        prompt = build_supervisor_prompt()

        assert "CONTENT TYPE TRIGGERS" in prompt
        assert "tutorial" in prompt.lower() or "guide" in prompt.lower()
        assert "security" in prompt.lower() or "auth" in prompt.lower()
        assert "performance" in prompt.lower() or "async" in prompt.lower()
        assert "comparison" in prompt.lower() or "vs" in prompt.lower()
        assert "FastAPI" in prompt or "React" in prompt or "Django" in prompt

    def test_supervisor_prompt_has_diverse_examples(self):
        """Test prompt has examples with varying agent counts (1, 3, 4, 5 agents)."""
        prompt = build_supervisor_prompt()

        # Check for examples with different agent counts
        # Should have at least one example with 1 agent, one with 3+, one with 4+
        examples_section = prompt.split("Examples:")[1] if "Examples:" in prompt else ""

        # Count agents in each example
        import re

        # Find all agent lists in examples
        agent_lists = re.findall(r'"agents":\s*\[(.*?)\]', examples_section)

        agent_counts = []
        for agent_list in agent_lists:
            # Count agents in this list
            agents = [a.strip().strip('"') for a in agent_list.split(",") if a.strip()]
            agent_counts.append(len(agents))

        # Should have examples with different counts
        assert len(set(agent_counts)) >= 2, (
            f"Prompt should have examples with varying agent counts, got: {agent_counts}"
        )
        # Should have at least one example with 1 agent and one with 3+ agents
        assert 1 in agent_counts or min(agent_counts) <= 2, (
            f"Should have example with 1-2 agents, got: {agent_counts}"
        )
        assert max(agent_counts) >= 3, f"Should have example with 3+ agents, got: {agent_counts}"
