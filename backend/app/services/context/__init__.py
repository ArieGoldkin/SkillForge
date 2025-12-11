"""Context engineering services for Handle Pattern and Agent Memory.

This package implements Google ADK's Context Engineering patterns:
- ArtifactStore: Store large content as refs, load on-demand
- SectionExtractor: Extract code blocks, headings for partial loading
- load_artifact tool: MCP tool for agents to load content sections
- search_memory tool: MCP tool for agents to search past analyses (RAG)
- SessionCompactor: Compact conversation history while keeping recent turns
- ContextCompiler: Build invocation-ready message lists with memory injection

Reference: https://google.github.io/adk-docs/sessions/context-engineering/
"""

from app.services.context.artifact_store import (
    ArtifactNotFoundError,
    ArtifactStore,
    ArtifactStoreError,
    InvalidURIError,
)
from app.services.context.compaction import (
    CompactionConfig,
    CompactionMetrics,
    CompiledContext,
    SessionCompactor,
)
from app.services.context.compiler import ContextCompiler
from app.services.context.memory_tools import MEMORY_TOOLS, search_memory
from app.services.context.section_extractor import SectionExtractor
from app.services.context.tools import ARTIFACT_TOOLS, load_artifact

__all__ = [
    "ARTIFACT_TOOLS",
    "MEMORY_TOOLS",
    "ArtifactNotFoundError",
    "ArtifactStore",
    "ArtifactStoreError",
    "CompactionConfig",
    "CompactionMetrics",
    "CompiledContext",
    "ContextCompiler",
    "InvalidURIError",
    "SectionExtractor",
    "SessionCompactor",
    "load_artifact",
    "search_memory",
]
