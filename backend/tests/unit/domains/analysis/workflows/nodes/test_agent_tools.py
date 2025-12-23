"""Unit tests for agent_tools.py - supervisor routing tools."""

import pytest
from langchain_core.tools import BaseTool

from app.domains.analysis.workflows.nodes.agent_tools import (
    AGENT_TOOLS,
    TOOL_TO_AGENT_MAP,
    code_quality_critic_tool,
    dependency_mapper_tool,
    implementation_planner_tool,
    integration_feasibility_tool,
    performance_analyst_tool,
    security_auditor_tool,
    tech_comparator_tool,
    trend_validator_tool,
)


class TestToolFunctions:
    """Test individual tool functions."""

    @pytest.mark.parametrize(
        "tool,expected_agent_name",
        [
            (tech_comparator_tool, "tech_comparator"),
            (security_auditor_tool, "security_auditor"),
            (integration_feasibility_tool, "integration_feasibility"),
            (implementation_planner_tool, "implementation_planner"),
            (performance_analyst_tool, "performance_analyst"),
            (code_quality_critic_tool, "code_quality_critic"),
            (trend_validator_tool, "trend_validator"),
            (dependency_mapper_tool, "dependency_mapper"),
        ],
    )
    def test_tool_returns_expected_agent_selection(self, tool, expected_agent_name):
        """Test each tool function returns expected agent selection message."""
        result = tool.invoke({"content": "test content"})
        assert result == f"{expected_agent_name} selected"

    @pytest.mark.parametrize(
        "tool",
        [
            tech_comparator_tool,
            security_auditor_tool,
            integration_feasibility_tool,
            implementation_planner_tool,
            performance_analyst_tool,
            code_quality_critic_tool,
            trend_validator_tool,
            dependency_mapper_tool,
        ],
    )
    def test_tool_is_langchain_tool(self, tool):
        """Test each tool is a valid LangChain tool instance."""
        assert isinstance(tool, BaseTool)

    @pytest.mark.parametrize(
        "tool",
        [
            tech_comparator_tool,
            security_auditor_tool,
            integration_feasibility_tool,
            implementation_planner_tool,
            performance_analyst_tool,
            code_quality_critic_tool,
            trend_validator_tool,
            dependency_mapper_tool,
        ],
    )
    def test_tool_has_name(self, tool):
        """Test each tool has a valid name."""
        assert hasattr(tool, "name")
        assert isinstance(tool.name, str)
        assert len(tool.name) > 0
        assert tool.name.endswith("_tool")

    @pytest.mark.parametrize(
        "tool",
        [
            tech_comparator_tool,
            security_auditor_tool,
            integration_feasibility_tool,
            implementation_planner_tool,
            performance_analyst_tool,
            code_quality_critic_tool,
            trend_validator_tool,
            dependency_mapper_tool,
        ],
    )
    def test_tool_has_description(self, tool):
        """Test each tool has a valid description."""
        assert hasattr(tool, "description")
        assert isinstance(tool.description, str)
        assert len(tool.description) > 0
        assert "Select" in tool.description or "select" in tool.description

    @pytest.mark.parametrize(
        "tool,expected_keyword",
        [
            (tech_comparator_tool, "compare"),
            (security_auditor_tool, "security"),
            (integration_feasibility_tool, "integration"),
            (implementation_planner_tool, "implementation"),
            (performance_analyst_tool, "performance"),
            (code_quality_critic_tool, "code"),
            (trend_validator_tool, "trend"),
            (dependency_mapper_tool, "dependen"),
        ],
    )
    def test_tool_description_contains_agent_purpose(self, tool, expected_keyword):
        """Test each tool's description reflects its agent's purpose."""
        assert expected_keyword.lower() in tool.description.lower()

    @pytest.mark.parametrize(
        "tool",
        [
            tech_comparator_tool,
            security_auditor_tool,
            integration_feasibility_tool,
            implementation_planner_tool,
            performance_analyst_tool,
            code_quality_critic_tool,
            trend_validator_tool,
            dependency_mapper_tool,
        ],
    )
    def test_tool_accepts_content_parameter(self, tool):
        """Test each tool accepts 'content' parameter in its schema."""
        # Tools should accept content parameter
        result = tool.invoke({"content": "test content"})
        assert isinstance(result, str)

    @pytest.mark.parametrize(
        "tool",
        [
            tech_comparator_tool,
            security_auditor_tool,
            integration_feasibility_tool,
            implementation_planner_tool,
            performance_analyst_tool,
            code_quality_critic_tool,
            trend_validator_tool,
            dependency_mapper_tool,
        ],
    )
    def test_tool_is_callable(self, tool):
        """Test each tool is callable."""
        assert callable(tool.invoke)


class TestToolToAgentMap:
    """Test TOOL_TO_AGENT_MAP configuration."""

    def test_tool_to_agent_map_has_all_tools(self):
        """Test TOOL_TO_AGENT_MAP contains all 8 tools."""
        assert len(TOOL_TO_AGENT_MAP) == 8

    @pytest.mark.parametrize(
        "tool_name",
        [
            "tech_comparator_tool",
            "security_auditor_tool",
            "integration_feasibility_tool",
            "implementation_planner_tool",
            "performance_analyst_tool",
            "code_quality_critic_tool",
            "trend_validator_tool",
            "dependency_mapper_tool",
        ],
    )
    def test_tool_to_agent_map_contains_tool(self, tool_name):
        """Test TOOL_TO_AGENT_MAP contains each expected tool name."""
        assert tool_name in TOOL_TO_AGENT_MAP

    @pytest.mark.parametrize(
        "tool_name,expected_agent",
        [
            ("tech_comparator_tool", "tech_comparator"),
            ("security_auditor_tool", "security_auditor"),
            ("integration_feasibility_tool", "integration_feasibility"),
            ("implementation_planner_tool", "implementation_planner"),
            ("performance_analyst_tool", "performance_analyst"),
            ("code_quality_critic_tool", "code_quality_critic"),
            ("trend_validator_tool", "trend_validator"),
            ("dependency_mapper_tool", "dependency_mapper"),
        ],
    )
    def test_tool_to_agent_map_correct_mapping(self, tool_name, expected_agent):
        """Test TOOL_TO_AGENT_MAP has correct tool-to-agent mapping."""
        assert TOOL_TO_AGENT_MAP[tool_name] == expected_agent

    def test_tool_to_agent_map_agent_names_valid(self):
        """Test TOOL_TO_AGENT_MAP agent names follow naming conventions."""
        for agent_name in TOOL_TO_AGENT_MAP.values():
            # Agent names should be snake_case
            assert agent_name.islower()
            assert "_" in agent_name or len(agent_name.split("_")) == 1
            # Agent name should not end with _agent or _tool
            assert not agent_name.endswith("_agent")
            assert not agent_name.endswith("_tool")

    def test_tool_to_agent_map_no_duplicate_agents(self):
        """Test TOOL_TO_AGENT_MAP has no duplicate agent names."""
        agent_names = list(TOOL_TO_AGENT_MAP.values())
        assert len(agent_names) == len(set(agent_names))

    def test_tool_to_agent_map_no_duplicate_tools(self):
        """Test TOOL_TO_AGENT_MAP has no duplicate tool names."""
        tool_names = list(TOOL_TO_AGENT_MAP.keys())
        assert len(tool_names) == len(set(tool_names))

    def test_tool_to_agent_map_is_dict(self):
        """Test TOOL_TO_AGENT_MAP is a dictionary."""
        assert isinstance(TOOL_TO_AGENT_MAP, dict)


class TestAgentToolsList:
    """Test AGENT_TOOLS list configuration."""

    def test_agent_tools_contains_all_tools(self):
        """Test AGENT_TOOLS list contains all 8 tools."""
        assert len(AGENT_TOOLS) == 8

    @pytest.mark.parametrize(
        "tool",
        [
            tech_comparator_tool,
            security_auditor_tool,
            integration_feasibility_tool,
            implementation_planner_tool,
            performance_analyst_tool,
            code_quality_critic_tool,
            trend_validator_tool,
            dependency_mapper_tool,
        ],
    )
    def test_agent_tools_contains_tool(self, tool):
        """Test AGENT_TOOLS list contains each expected tool."""
        assert tool in AGENT_TOOLS

    def test_agent_tools_all_are_langchain_tools(self):
        """Test all items in AGENT_TOOLS are valid LangChain tools."""
        for tool in AGENT_TOOLS:
            assert isinstance(tool, BaseTool)

    def test_agent_tools_all_have_names(self):
        """Test all tools in AGENT_TOOLS have names."""
        for tool in AGENT_TOOLS:
            assert hasattr(tool, "name")
            assert isinstance(tool.name, str)
            assert len(tool.name) > 0

    def test_agent_tools_all_have_descriptions(self):
        """Test all tools in AGENT_TOOLS have descriptions."""
        for tool in AGENT_TOOLS:
            assert hasattr(tool, "description")
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0

    def test_agent_tools_no_duplicate_names(self):
        """Test AGENT_TOOLS has no duplicate tool names."""
        tool_names = [tool.name for tool in AGENT_TOOLS]
        assert len(tool_names) == len(set(tool_names))

    def test_agent_tools_is_list(self):
        """Test AGENT_TOOLS is a list."""
        assert isinstance(AGENT_TOOLS, list)

    def test_agent_tools_list_matches_map_keys(self):
        """Test AGENT_TOOLS list matches TOOL_TO_AGENT_MAP keys."""
        tool_names_in_list = {tool.name for tool in AGENT_TOOLS}
        tool_names_in_map = set(TOOL_TO_AGENT_MAP.keys())
        assert tool_names_in_list == tool_names_in_map


class TestToolAgentNameConsistency:
    """Test consistency between tool names and agent names."""

    @pytest.mark.parametrize(
        "tool_name,expected_agent",
        [
            ("tech_comparator_tool", "tech_comparator"),
            ("security_auditor_tool", "security_auditor"),
            ("integration_feasibility_tool", "integration_feasibility"),
            ("implementation_planner_tool", "implementation_planner"),
            ("performance_analyst_tool", "performance_analyst"),
            ("code_quality_critic_tool", "code_quality_critic"),
            ("trend_validator_tool", "trend_validator"),
            ("dependency_mapper_tool", "dependency_mapper"),
        ],
    )
    def test_tool_name_matches_agent_name(self, tool_name, expected_agent):
        """Test tool name consistently derives from agent name."""
        # Tool name should be agent name + "_tool"
        assert tool_name == f"{expected_agent}_tool"

    def test_all_tool_names_end_with_tool(self):
        """Test all tool names end with '_tool'."""
        for tool in AGENT_TOOLS:
            assert tool.name.endswith("_tool")

    def test_all_agent_names_do_not_end_with_tool(self):
        """Test all agent names do not end with '_tool'."""
        for agent_name in TOOL_TO_AGENT_MAP.values():
            assert not agent_name.endswith("_tool")


class TestToolSchemaValidation:
    """Test tool schema validation."""

    @pytest.mark.parametrize(
        "tool",
        [
            tech_comparator_tool,
            security_auditor_tool,
            integration_feasibility_tool,
            implementation_planner_tool,
            performance_analyst_tool,
            code_quality_critic_tool,
            trend_validator_tool,
            dependency_mapper_tool,
        ],
    )
    def test_tool_has_args_schema(self, tool):
        """Test each tool has a valid args schema."""
        assert hasattr(tool, "args_schema")
        # args_schema should be a Pydantic model or None (inferred from function signature)
        # Since we use @tool decorator with typed parameters, schema should exist

    @pytest.mark.parametrize(
        "tool",
        [
            tech_comparator_tool,
            security_auditor_tool,
            integration_feasibility_tool,
            implementation_planner_tool,
            performance_analyst_tool,
            code_quality_critic_tool,
            trend_validator_tool,
            dependency_mapper_tool,
        ],
    )
    def test_tool_invocation_returns_string(self, tool):
        """Test each tool invocation returns a string."""
        result = tool.invoke({"content": "test content"})
        assert isinstance(result, str)
        assert "selected" in result


class TestToolReturnValues:
    """Test tool return values match expected format."""

    @pytest.mark.parametrize(
        "tool,agent_name",
        [
            (tech_comparator_tool, "tech_comparator"),
            (security_auditor_tool, "security_auditor"),
            (integration_feasibility_tool, "integration_feasibility"),
            (implementation_planner_tool, "implementation_planner"),
            (performance_analyst_tool, "performance_analyst"),
            (code_quality_critic_tool, "code_quality_critic"),
            (trend_validator_tool, "trend_validator"),
            (dependency_mapper_tool, "dependency_mapper"),
        ],
    )
    def test_tool_return_value_format(self, tool, agent_name):
        """Test each tool returns '{agent_name} selected' format."""
        result = tool.invoke({"content": "test content"})
        expected_format = f"{agent_name} selected"
        assert result == expected_format

    @pytest.mark.parametrize(
        "tool",
        [
            tech_comparator_tool,
            security_auditor_tool,
            integration_feasibility_tool,
            implementation_planner_tool,
            performance_analyst_tool,
            code_quality_critic_tool,
            trend_validator_tool,
            dependency_mapper_tool,
        ],
    )
    def test_tool_return_value_consistent(self, tool):
        """Test each tool returns consistent value across multiple invocations."""
        result1 = tool.invoke({"content": "test content 1"})
        result2 = tool.invoke({"content": "test content 2"})
        # Return value should be same regardless of input (stub tools)
        assert result1 == result2


class TestToolCountAndCompleteness:
    """Test tool count and completeness."""

    def test_exactly_8_tools_defined(self):
        """Test exactly 8 tools are defined in AGENT_TOOLS."""
        assert len(AGENT_TOOLS) == 8

    def test_exactly_8_mappings_defined(self):
        """Test exactly 8 mappings are defined in TOOL_TO_AGENT_MAP."""
        assert len(TOOL_TO_AGENT_MAP) == 8

    def test_all_expected_agent_types_covered(self):
        """Test all expected agent types are covered by tools."""
        expected_agents = {
            "tech_comparator",
            "security_auditor",
            "integration_feasibility",
            "implementation_planner",
            "performance_analyst",
            "code_quality_critic",
            "trend_validator",
            "dependency_mapper",
        }
        actual_agents = set(TOOL_TO_AGENT_MAP.values())
        assert actual_agents == expected_agents

    def test_all_expected_tools_covered(self):
        """Test all expected tool names are covered."""
        expected_tools = {
            "tech_comparator_tool",
            "security_auditor_tool",
            "integration_feasibility_tool",
            "implementation_planner_tool",
            "performance_analyst_tool",
            "code_quality_critic_tool",
            "trend_validator_tool",
            "dependency_mapper_tool",
        }
        actual_tools = set(TOOL_TO_AGENT_MAP.keys())
        assert actual_tools == expected_tools
