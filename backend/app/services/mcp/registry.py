"""Tool registry for agent capability mapping.

Manages which MCP tools each agent can access, preventing tool overload
and ensuring agents only see relevant capabilities.

Agent Tool Access:
    - security_auditor: GitHub security advisories, code search
    - dependency_mapper: npm/pypi package info, GitHub repo details
    - tech_comparator: npm/github stats for comparison
    - code_quality_critic: GitHub commit history, repo details
    - implementation_planner: No tools (generates plans from context)
    - performance_analyst: No tools (analyzes metrics)
    - trend_validator: No tools (validates trends)
    - integration_feasibility: No tools (assesses feasibility)

Example:
    >>> registry = ToolRegistry()
    >>> if registry.is_tool_enabled("security_auditor"):
    ...     tools = registry.filter_tools(all_tools, "security_auditor")
    ...     # Only GitHub security tools available

"""

from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.tools import BaseTool

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ToolCapability:
    """Describes a single MCP tool capability.

    Capabilities identify which specific tool from which MCP server
    an agent can use, formatted as "server:tool_name".

    Attributes:
        server: MCP server name (e.g., "github", "npm", "pypi")
        tool_name: Specific tool name (e.g., "get_repo", "search_packages")
        description: Optional human-readable description of capability

    Example:
        >>> capability = ToolCapability(
        ...     server="github",
        ...     tool_name="get_security_advisories",
        ...     description="Search CVE database for security issues",
        ... )
        >>> capability.capability_id
        'github:get_security_advisories'

    """

    server: str
    tool_name: str
    description: str = ""

    @property
    def capability_id(self) -> str:
        """Return capability in server:tool format.

        Returns:
            Capability identifier as "server:tool_name"

        """
        return f"{self.server}:{self.tool_name}"


@dataclass
class AgentToolConfig:
    """Configuration for an agent's tool access.

    Controls which tools an agent can use, with rate limiting and timeouts
    to prevent resource exhaustion.

    Attributes:
        agent_type: Agent identifier (e.g., "security_auditor")
        enabled: Whether agent can use tools (default: False)
        capabilities: List of tool capabilities agent can access
        max_tool_calls: Maximum calls per analysis (default: 10)
        tool_timeout: Timeout per tool call in seconds (default: 30.0)

    Example:
        >>> config = AgentToolConfig(
        ...     agent_type="security_auditor",
        ...     enabled=True,
        ...     capabilities=[
        ...         ToolCapability("github", "search_code"),
        ...         ToolCapability("github", "get_security_advisories"),
        ...     ],
        ...     max_tool_calls=15,
        ... )

    """

    agent_type: str
    enabled: bool = False
    capabilities: list[ToolCapability] = field(default_factory=list)
    max_tool_calls: int = 10
    tool_timeout: float = 30.0


# Default agent tool configurations
# These can be overridden at runtime via ToolRegistry initialization
AGENT_TOOL_CONFIGS: dict[str, AgentToolConfig] = {
    "security_auditor": AgentToolConfig(
        agent_type="security_auditor",
        enabled=True,
        capabilities=[
            ToolCapability(
                server="github",
                tool_name="search_code",
                description="Search GitHub for vulnerable code patterns",
            ),
            ToolCapability(
                server="github",
                tool_name="get_security_advisories",
                description="Fetch CVE and security advisory data",
            ),
        ],
        max_tool_calls=15,
        tool_timeout=30.0,
    ),
    "dependency_mapper": AgentToolConfig(
        agent_type="dependency_mapper",
        enabled=True,
        capabilities=[
            ToolCapability(
                server="npm",
                tool_name="get_package",
                description="Get npm package metadata and dependencies",
            ),
            ToolCapability(
                server="pypi",
                tool_name="get_package",
                description="Get PyPI package metadata and dependencies",
            ),
            ToolCapability(
                server="github",
                tool_name="get_repo",
                description="Get repository details and metadata",
            ),
        ],
        max_tool_calls=20,
        tool_timeout=25.0,
    ),
    "tech_comparator": AgentToolConfig(
        agent_type="tech_comparator",
        enabled=True,
        capabilities=[
            ToolCapability(
                server="npm",
                tool_name="get_package",
                description="Get npm package stats for comparison",
            ),
            ToolCapability(
                server="github",
                tool_name="get_repo",
                description="Get repository stats for comparison",
            ),
        ],
        max_tool_calls=10,
        tool_timeout=20.0,
    ),
    "code_quality_critic": AgentToolConfig(
        agent_type="code_quality_critic",
        enabled=True,
        capabilities=[
            ToolCapability(
                server="github",
                tool_name="list_commits",
                description="Analyze commit history for quality patterns",
            ),
            ToolCapability(
                server="github",
                tool_name="get_repo",
                description="Get repository metadata for quality assessment",
            ),
        ],
        max_tool_calls=12,
        tool_timeout=25.0,
    ),
    "implementation_planner": AgentToolConfig(
        agent_type="implementation_planner",
        enabled=False,
        capabilities=[],
        max_tool_calls=0,
        tool_timeout=0.0,
    ),
    "performance_analyst": AgentToolConfig(
        agent_type="performance_analyst",
        enabled=False,
        capabilities=[],
        max_tool_calls=0,
        tool_timeout=0.0,
    ),
    "trend_validator": AgentToolConfig(
        agent_type="trend_validator",
        enabled=False,
        capabilities=[],
        max_tool_calls=0,
        tool_timeout=0.0,
    ),
    "integration_feasibility": AgentToolConfig(
        agent_type="integration_feasibility",
        enabled=False,
        capabilities=[],
        max_tool_calls=0,
        tool_timeout=0.0,
    ),
}


class ToolRegistry:
    """Registry for managing agent tool access.

    Controls which MCP tools each agent can use, preventing tool overload
    and ensuring agents only see relevant capabilities.

    The registry maintains a mapping of agent types to their allowed tools,
    with support for runtime configuration updates.

    Attributes:
        _agent_configs: Dictionary mapping agent type to configuration

    Example:
        >>> registry = ToolRegistry()
        >>> # Check if agent can use tools
        >>> if registry.is_tool_enabled("security_auditor"):
        ...     # Get filtered tools for agent
        ...     agent_tools = registry.filter_tools(all_tools, "security_auditor")
        ...     # Only GitHub security tools will be included

        >>> # Register custom agent configuration
        >>> custom_config = AgentToolConfig(
        ...     agent_type="custom_agent",
        ...     enabled=True,
        ...     capabilities=[ToolCapability("github", "search_code")],
        ... )
        >>> registry.register_agent(custom_config)

    """

    def __init__(self, agent_configs: dict[str, AgentToolConfig] | None = None) -> None:
        """Initialize registry with default or custom configurations.

        Args:
            agent_configs: Optional custom agent configurations.
                          If None, uses AGENT_TOOL_CONFIGS defaults.

        """
        self._agent_configs = (
            agent_configs if agent_configs is not None else AGENT_TOOL_CONFIGS.copy()
        )
        logger.info(
            "initialized_tool_registry",
            agent_count=len(self._agent_configs),
            enabled_agents=len(self.list_enabled_agents()),
        )

    def get_agent_config(self, agent_type: str) -> AgentToolConfig:
        """Get configuration for specified agent.

        Args:
            agent_type: Agent identifier (e.g., "security_auditor")

        Returns:
            AgentToolConfig for the agent

        Raises:
            KeyError: If agent_type is not registered

        """
        if agent_type not in self._agent_configs:
            logger.warning("unknown_agent_type_requested", agent_type=agent_type)
            msg = f"Unknown agent type: {agent_type}"
            raise KeyError(msg)

        return self._agent_configs[agent_type]

    def is_tool_enabled(self, agent_type: str) -> bool:
        """Check if agent has tool access enabled and has capabilities.

        An agent is considered tool-enabled if:
        1. It has enabled=True in its configuration
        2. It has at least one capability defined

        Args:
            agent_type: Agent identifier

        Returns:
            True if agent can use tools, False otherwise

        """
        try:
            config = self.get_agent_config(agent_type)
            return config.enabled and len(config.capabilities) > 0
        except KeyError:
            return False

    def get_capabilities(self, agent_type: str) -> list[str]:
        """Get capability IDs for agent.

        Args:
            agent_type: Agent identifier

        Returns:
            List of capability IDs in "server:tool" format.
            Returns empty list if agent is disabled or unknown.

        Example:
            >>> registry.get_capabilities("security_auditor")
            ['github:search_code', 'github:get_security_advisories']

        """
        try:
            config = self.get_agent_config(agent_type)
            if not config.enabled:
                return []
            return [cap.capability_id for cap in config.capabilities]
        except KeyError:
            return []

    def filter_tools(self, tools: list[BaseTool], agent_type: str) -> list[BaseTool]:
        """Filter tools to only those matching agent's capabilities.

        Matches tools by name against agent's capability list.
        Tool names should follow the format "server_toolname" or match
        the tool_name directly.

        Args:
            tools: List of available MCP tools
            agent_type: Agent identifier

        Returns:
            Filtered list of tools agent can access.
            Returns empty list if agent has no tools enabled.

        Example:
            >>> all_tools = [github_search, npm_get_package, pypi_get_package]
            >>> security_tools = registry.filter_tools(all_tools, "security_auditor")
            >>> # Only github_search is returned

        """
        if not self.is_tool_enabled(agent_type):
            logger.debug("agent_tools_disabled", agent_type=agent_type)
            return []

        config = self.get_agent_config(agent_type)
        allowed_tool_names = {cap.tool_name for cap in config.capabilities}

        filtered = [tool for tool in tools if tool.name in allowed_tool_names]

        logger.info(
            "filtered_tools_for_agent",
            agent_type=agent_type,
            total_tools=len(tools),
            filtered_tools=len(filtered),
            allowed_capabilities=list(allowed_tool_names),
        )

        return filtered

    def register_agent(self, config: AgentToolConfig) -> None:
        """Register or update agent configuration.

        If agent already exists, its configuration is replaced.

        Args:
            config: Agent configuration to register

        """
        self._agent_configs[config.agent_type] = config
        logger.info(
            "registered_agent_config",
            agent_type=config.agent_type,
            enabled=config.enabled,
            capability_count=len(config.capabilities),
        )

    def list_enabled_agents(self) -> list[str]:
        """List agent types that have tools enabled.

        Returns:
            List of agent type identifiers with enabled=True and capabilities

        """
        return [
            agent_type
            for agent_type, config in self._agent_configs.items()
            if config.enabled and len(config.capabilities) > 0
        ]

    def get_all_required_servers(self) -> set[str]:
        """Get set of all MCP servers needed by enabled agents.

        This is useful for determining which MCP servers to initialize
        based on actual agent requirements.

        Returns:
            Set of server names (e.g., {"github", "npm", "pypi"})

        Example:
            >>> servers = registry.get_all_required_servers()
            >>> # Initialize only these MCP servers
            >>> for server in servers:
            ...     initialize_mcp_server(server)

        """
        servers = set()
        for config in self._agent_configs.values():
            if config.enabled:
                for capability in config.capabilities:
                    servers.add(capability.server)

        logger.debug("calculated_required_servers", servers=list(servers))
        return servers
