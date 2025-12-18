"""Cutting-edge topic templates for evaluation dataset generation.

This module provides templates for 4 cutting-edge topics (Dec 2025):
1. A2A Protocol (Google) - Agent-to-Agent communication
2. MCP Nov 2025 - Model Context Protocol updates
3. Context Engineering - Advanced prompt engineering
4. LangGraph Multi-Agent - Multi-agent orchestration

Each template includes:
- query_patterns: Example queries
- expected_topics: Key concepts to cover
- keywords: Important terms
- references: Documentation/blog URLs
- subdomain: Specific area within the topic
"""

from __future__ import annotations

from typing import TypedDict


class TopicTemplate(TypedDict):
    """Template for cutting-edge topic examples."""

    query_patterns: list[str]
    expected_topics: list[str]
    keywords: list[str]
    references: list[str]
    subdomain: str


# A2A Protocol (Google Agent-to-Agent Communication)
A2A_PROTOCOL_TEMPLATES: list[TopicTemplate] = [
    {
        "query_patterns": [
            "How does Google's A2A protocol work for agent communication?",
            "Implement A2A protocol for multi-agent coordination",
            "A2A protocol vs direct function calling for agent interactions",
        ],
        "expected_topics": [
            "Structured agent-to-agent messaging",
            "Protocol buffers for agent communication",
            "Asynchronous agent coordination",
            "Error handling in multi-agent systems",
        ],
        "keywords": [
            "A2A protocol",
            "agent communication",
            "Google agents",
            "structured messaging",
            "protocol buffers",
        ],
        "references": [
            "https://developers.googleblog.com/a2a-protocol",
            "https://github.com/google/a2a-protocol-spec",
        ],
        "subdomain": "agent_communication",
    },
    {
        "query_patterns": [
            "Best practices for A2A protocol error handling",
            "How to debug A2A agent communication failures?",
            "A2A protocol message validation patterns",
        ],
        "expected_topics": [
            "Error recovery strategies",
            "Message validation schemas",
            "Debugging tools for A2A",
            "Circuit breaker patterns",
        ],
        "keywords": [
            "error handling",
            "message validation",
            "debugging",
            "circuit breaker",
            "retry logic",
        ],
        "references": [
            "https://developers.googleblog.com/a2a-error-handling",
        ],
        "subdomain": "error_handling",
    },
    {
        "query_patterns": [
            "Scale A2A protocol to 100+ agents",
            "Performance optimization for A2A agent networks",
            "A2A protocol latency benchmarks",
        ],
        "expected_topics": [
            "Scalability patterns",
            "Message routing optimization",
            "Load balancing strategies",
            "Performance monitoring",
        ],
        "keywords": [
            "scalability",
            "performance",
            "message routing",
            "load balancing",
            "latency optimization",
        ],
        "references": [
            "https://developers.googleblog.com/a2a-scalability",
        ],
        "subdomain": "scalability",
    },
]

# MCP Nov 2025 (Model Context Protocol Updates)
MCP_NOV_2025_TEMPLATES: list[TopicTemplate] = [
    {
        "query_patterns": [
            "What's new in MCP November 2025 release?",
            "Migrate from MCP 1.0 to November 2025 version",
            "MCP Nov 2025 breaking changes and migration guide",
        ],
        "expected_topics": [
            "Resource templates feature",
            "Improved server discovery",
            "Enhanced security model",
            "Backward compatibility considerations",
        ],
        "keywords": [
            "MCP Nov 2025",
            "resource templates",
            "server discovery",
            "breaking changes",
            "migration",
        ],
        "references": [
            "https://modelcontextprotocol.io/changelog/2025-11",
            "https://github.com/modelcontextprotocol/spec/releases/nov-2025",
        ],
        "subdomain": "mcp_updates",
    },
    {
        "query_patterns": [
            "Use MCP resource templates in production",
            "Best practices for MCP resource templates",
            "MCP resource templates vs static resources",
        ],
        "expected_topics": [
            "Dynamic resource generation",
            "Template syntax and variables",
            "Performance implications",
            "Caching strategies",
        ],
        "keywords": [
            "resource templates",
            "dynamic resources",
            "template syntax",
            "caching",
            "performance",
        ],
        "references": [
            "https://modelcontextprotocol.io/docs/resource-templates",
        ],
        "subdomain": "resource_templates",
    },
    {
        "query_patterns": [
            "Secure MCP server configuration Nov 2025",
            "MCP Nov 2025 security best practices",
            "Authentication changes in MCP Nov 2025",
        ],
        "expected_topics": [
            "New authentication mechanisms",
            "Authorization patterns",
            "Security audit recommendations",
            "Credential management",
        ],
        "keywords": [
            "security",
            "authentication",
            "authorization",
            "credentials",
            "audit",
        ],
        "references": [
            "https://modelcontextprotocol.io/security/nov-2025",
        ],
        "subdomain": "security",
    },
]

# Context Engineering (Advanced Prompt Engineering)
CONTEXT_ENGINEERING_TEMPLATES: list[TopicTemplate] = [
    {
        "query_patterns": [
            "What is context engineering vs prompt engineering?",
            "Implement context engineering for GPT-4o",
            "Context engineering best practices 2025",
        ],
        "expected_topics": [
            "Context window optimization",
            "Structured context injection",
            "Dynamic context management",
            "Token budget allocation",
        ],
        "keywords": [
            "context engineering",
            "prompt engineering",
            "context window",
            "token optimization",
            "structured context",
        ],
        "references": [
            "https://anthropic.com/context-engineering-guide",
            "https://openai.com/research/context-optimization",
        ],
        "subdomain": "context_optimization",
    },
    {
        "query_patterns": [
            "Multi-turn context preservation strategies",
            "How to maintain context across long conversations?",
            "Context compression techniques for LLMs",
        ],
        "expected_topics": [
            "Context summarization",
            "Hierarchical context structures",
            "Context pruning strategies",
            "Memory-augmented generation",
        ],
        "keywords": [
            "multi-turn",
            "context preservation",
            "summarization",
            "context compression",
            "memory",
        ],
        "references": [
            "https://arxiv.org/abs/2025.context-compression",
        ],
        "subdomain": "multi_turn",
    },
    {
        "query_patterns": [
            "RAG-enhanced context engineering patterns",
            "Combine RAG with context engineering",
            "Context engineering for retrieval-augmented generation",
        ],
        "expected_topics": [
            "RAG integration patterns",
            "Context-aware retrieval",
            "Hybrid context sources",
            "Quality-weighted context injection",
        ],
        "keywords": [
            "RAG",
            "retrieval",
            "hybrid context",
            "context injection",
            "quality weighting",
        ],
        "references": [
            "https://anthropic.com/rag-context-engineering",
        ],
        "subdomain": "rag_integration",
    },
]

# LangGraph Multi-Agent (Advanced Orchestration)
LANGGRAPH_MULTIAGENT_TEMPLATES: list[TopicTemplate] = [
    {
        "query_patterns": [
            "Build production multi-agent system with LangGraph",
            "LangGraph multi-agent orchestration patterns",
            "Scale LangGraph to 10+ specialized agents",
        ],
        "expected_topics": [
            "Supervisor-worker patterns",
            "Agent state management",
            "Inter-agent communication",
            "Error recovery strategies",
        ],
        "keywords": [
            "LangGraph",
            "multi-agent",
            "supervisor",
            "orchestration",
            "state management",
        ],
        "references": [
            "https://langchain-ai.github.io/langgraph/multi-agent",
            "https://blog.langchain.dev/langgraph-multi-agent-workflows",
        ],
        "subdomain": "orchestration",
    },
    {
        "query_patterns": [
            "Implement dynamic agent routing in LangGraph",
            "LangGraph conditional agent selection",
            "Route between agents based on query complexity",
        ],
        "expected_topics": [
            "Conditional edges",
            "Dynamic routing logic",
            "Query classification",
            "Routing performance optimization",
        ],
        "keywords": [
            "dynamic routing",
            "conditional edges",
            "query classification",
            "agent selection",
            "routing logic",
        ],
        "references": [
            "https://langchain-ai.github.io/langgraph/conditional-edges",
        ],
        "subdomain": "routing",
    },
    {
        "query_patterns": [
            "LangGraph persistent checkpointing for multi-agent systems",
            "Resume failed multi-agent workflows with LangGraph",
            "LangGraph checkpoint strategies for production",
        ],
        "expected_topics": [
            "Checkpoint mechanisms",
            "State persistence",
            "Workflow recovery",
            "Database-backed checkpoints",
        ],
        "keywords": [
            "checkpointing",
            "persistence",
            "state recovery",
            "workflow resume",
            "database",
        ],
        "references": [
            "https://langchain-ai.github.io/langgraph/checkpointing",
        ],
        "subdomain": "checkpointing",
    },
    {
        "query_patterns": [
            "Monitor and debug LangGraph multi-agent systems",
            "LangGraph observability for production agents",
            "Trace multi-agent execution in LangGraph",
        ],
        "expected_topics": [
            "Langfuse integration",
            "Tracing and logging",
            "Performance metrics",
            "Debugging tools",
        ],
        "keywords": [
            "observability",
            "Langfuse",
            "tracing",
            "debugging",
            "monitoring",
        ],
        "references": [
            "https://langchain-ai.github.io/langgraph/observability",
            "https://smith.langchain.com",
        ],
        "subdomain": "observability",
    },
]

# Aggregate all templates by topic
ALL_TEMPLATES: dict[str, list[TopicTemplate]] = {
    "a2a_protocol": A2A_PROTOCOL_TEMPLATES,
    "mcp_nov_2025": MCP_NOV_2025_TEMPLATES,
    "context_engineering": CONTEXT_ENGINEERING_TEMPLATES,
    "langgraph_multiagent": LANGGRAPH_MULTIAGENT_TEMPLATES,
}
