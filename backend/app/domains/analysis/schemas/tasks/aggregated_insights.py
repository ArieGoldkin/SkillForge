"""Aggregated insights schema for synthesis output.

Enhanced for triple-purpose consumption:
1. AI Coding Assistants (Claude Code, Cursor, Windsurf, Copilot)
2. Tutor System (syllabus generation, lessons, exercises)
3. Human Readers (documentation, learning, reference)

Related: Issue #302 - Triple-Purpose Schema Enhancement
"""

from pydantic import BaseModel, Field, model_validator


class GotchaItem(BaseModel):
    """Common pitfall with symptom and quick fix."""

    issue: str = Field(
        description=(
            "Description of the common pitfall or gotcha. "
            "Be specific and technical (e.g., 'Circular imports between modules')"
        )
    )
    symptom: str = Field(
        description=(
            "Observable symptom when this issue occurs. "
            "Should help developers recognize the problem "
            "(e.g., 'ImportError: cannot import name X from Y')"
        )
    )
    quick_fix: str = Field(
        description=(
            "Concrete solution or workaround. "
            "Should be actionable and specific "
            "(e.g., 'Use TYPE_CHECKING import guard and string type hints')"
        )
    )


class QuickReference(BaseModel):
    """Front-loaded critical information for fast scanning.

    This section appears at the top of artifacts to provide instant context
    for developers and AI agents. Designed for 10-15 second scanning per
    research findings (docs/ARTIFACT_RESEARCH_SUMMARY.md).
    """

    primary_technology: str = Field(
        description=(
            "Main technology stack with specific versions. "
            "Format: 'TechName version + optional dependency'. "
            "Example: 'LangGraph 0.6.7 + PostgreSQL 14' or 'React 19 + Next.js 15'"
        ),
        min_length=5,
        max_length=100,
    )
    complexity: str = Field(
        description=(
            "Complexity level with time estimate. "
            "Format: 'Level (Est. X-Y hours)'. "
            "Levels: Beginner (1-2h), Intermediate (3-4h), Advanced (5-8h), Expert (8+h). "
            "Example: 'Intermediate (Est. 3-4 hours)'"
        ),
        min_length=10,
        max_length=60,
    )
    prerequisites: list[str] = Field(
        description=(
            "Required dependencies or knowledge before starting. "
            "Max 4 items, each specific and version-pinned. "
            "Example: 'Python 3.11+', 'PostgreSQL 14+', 'Docker installed'"
        ),
        max_length=4,
        default_factory=list,
    )
    critical_commands: list[str] = Field(
        description=(
            "Essential commands for installation and setup. "
            "Max 6 items, copy-paste ready with exact versions. "
            "Example: 'pip install langgraph==0.6.7', 'docker-compose up -d'"
        ),
        max_length=6,
        default_factory=list,
    )
    files_to_modify: list[str] = Field(
        description=(
            "List of files to create or modify with full paths. "
            "Max 10 items, prioritize most important files first. "
            "Example: 'backend/app/workflows/graph.py', 'backend/app/models/state.py'"
        ),
        max_length=10,
        default_factory=list,
    )
    files_disclaimer: str = Field(
        default="⚠️ AI-suggested structure based on content patterns. Adapt to your project.",
        description=(
            "Disclaimer that files are suggestions, not from source. "
            "Issue #299-304: Prevents hallucination confusion by clarifying that "
            "files_to_modify are AI-generated suggestions based on content patterns, "
            "not actual file paths from the source document."
        ),
    )
    gotchas: list[GotchaItem] = Field(
        description=(
            "Common pitfalls with symptoms and quick fixes. "
            "Max 5 items, prioritize most frequent or critical issues. "
            "Helps developers avoid common mistakes and debug faster."
        ),
        max_length=5,
        default_factory=list,
    )


class ConflictResolution(BaseModel):
    """Conflict resolution details."""

    conflict: str = Field(description="Description of the contradiction between agents")
    resolution: str = Field(description="How the conflict was resolved")
    priority_agent: str = Field(description="Which agent's finding was prioritized")
    reasoning: str = Field(description="Why this agent was prioritized")


class CoverageGap(BaseModel):
    """Missing analysis perspective."""

    missing_agent: str = Field(description="Agent that did not contribute")
    missing_perspective: str = Field(description="What analysis is missing")
    impact: str = Field(description="How this gap affects the analysis")


class CrossDomainConnection(BaseModel):
    """Connection between different analysis domains."""

    domains: list[str] = Field(
        description="The two domains connected (e.g., ['security', 'performance'])",
        min_length=2,
        max_length=2,
    )
    connection: str = Field(description="The identified relationship or trade-off")
    agents_involved: list[str] = Field(
        description="Agents that contributed to this insight", min_length=2
    )


class TLDRSection(BaseModel):
    """Executive summary optimized for human scanning (10-30 seconds).

    Provides immediate value for busy developers and learners who need
    to quickly assess whether the content is relevant to their needs.
    """

    summary: str = Field(
        description=(
            "2-3 sentence overview of what this content teaches. "
            "Focus on the 'what' and 'why', not the 'how'. "
            "Example: 'This guide teaches vector database optimization for RAG systems. "
            "You will learn how to reduce latency by 60% through proper indexing and chunking strategies.'"
        ),
        min_length=50,
        max_length=500,
    )
    key_takeaways: list[str] = Field(
        description=(
            "3-5 concrete outcomes or skills the reader will gain. "
            "Each should be specific and measurable. "
            "Example: 'Build a production-ready RAG pipeline with <200ms query latency'"
        ),
        min_length=3,
        max_length=5,
    )
    time_to_implement: str = Field(
        description=(
            "Realistic time estimate with breakdown. "
            "Format: 'Total time (breakdown)'. "
            "Example: '4-6 hours (2h setup, 2h implementation, 1-2h testing)'"
        ),
        min_length=10,
        max_length=100,
    )


class CoreConcept(BaseModel):
    """Fundamental concept with learning-oriented context.

    Designed for both human understanding and AI assistant context building.
    Each concept includes pedagogical metadata for tutorial generation.
    """

    name: str = Field(
        description="Concept name, clear and searchable (e.g., 'Semantic Chunking')",
        min_length=2,
        max_length=100,
    )
    definition: str = Field(
        description=(
            "Clear, jargon-free explanation of the concept. "
            "Assume intelligent reader but no prior knowledge of this specific topic. "
            "2-3 sentences maximum."
        ),
        min_length=50,
        max_length=500,
    )
    why_it_matters: str = Field(
        description=(
            "Practical importance and real-world impact. "
            "Answers: 'Why should I learn this?' "
            "Example: 'Improves retrieval accuracy by 40% compared to fixed-size chunks'"
        ),
        min_length=30,
        max_length=300,
    )
    related_concepts: list[str] = Field(
        description=(
            "Connected concepts for knowledge graph building. "
            "Max 5 related topics that learners should explore. "
            "Example: 'Vector Embeddings', 'Cosine Similarity', 'Context Windows'"
        ),
        max_length=5,
        default_factory=list,
    )
    complexity_level: str = Field(
        description=(
            "Learning difficulty level. "
            "Options: 'Beginner', 'Intermediate', 'Advanced', 'Expert'. "
            "Helps tutor system sequence concepts appropriately."
        ),
        pattern="^(Beginner|Intermediate|Advanced|Expert)$",
    )


class AIAssistantPrompt(BaseModel):
    """Pre-formatted prompt for AI coding assistants (Claude, Cursor, Copilot).

    Provides context and scaffolding that AI assistants need to generate
    correct, production-ready code on first attempt.
    """

    context: str = Field(
        description=(
            "Background information and architectural context. "
            "Explains 'where this fits' in the larger system. "
            "Example: 'This RAG pipeline runs in a FastAPI async endpoint, "
            "querying PostgreSQL with pgvector extension for semantic search.'"
        ),
        min_length=50,
        max_length=1000,
    )
    implementation_steps: list[str] = Field(
        description=(
            "Ordered implementation checklist, each step actionable. "
            "Format: Imperative commands (e.g., 'Create', 'Install', 'Configure'). "
            "5-10 steps maximum for manageable scope."
        ),
        min_length=5,
        max_length=10,
    )
    code_snippets: dict[str, str] = Field(
        description=(
            "Key code examples by purpose, not by file. "
            "Keys: descriptive names (e.g., 'vector_search_query', 'embedding_function'). "
            "Values: Complete, runnable code snippets with comments. "
            "Max 5 snippets to avoid overwhelming the context window."
        ),
        default_factory=dict,
    )
    file_structure: dict[str, str] = Field(
        description=(
            "Expected file tree with purpose annotations. "
            "Keys: file paths (e.g., 'app/services/rag.py'). "
            "Values: one-line description of file's responsibility. "
            "Helps AI assistants understand module boundaries."
        ),
        default_factory=dict,
    )
    success_criteria: list[str] = Field(
        description=(
            "Testable outcomes to verify correct implementation. "
            "Each criterion should be specific and verifiable. "
            "Example: 'Query latency <200ms for 1000 document corpus', "
            "'Recall@10 >0.85 on golden dataset'"
        ),
        min_length=3,
        max_length=7,
    )


class QuizQuestion(BaseModel):
    """Multiple-choice or true/false question for self-assessment.

    Used by tutor system to generate quizzes and validate understanding.
    """

    question: str = Field(
        description="Clear, unambiguous question testing a specific concept",
        min_length=10,
        max_length=300,
    )
    options: list[str] = Field(
        description=(
            "Answer choices (2-5 options). "
            "For true/false, use ['True', 'False']. "
            "For multiple choice, include plausible distractors."
        ),
        min_length=2,
        max_length=5,
    )
    correct_answer: str = Field(
        description=(
            "The correct option (must exactly match one of the options). "
            "Example: 'True' or 'Semantic chunking improves retrieval accuracy'"
        ),
        min_length=1,
        max_length=300,
    )
    explanation: str = Field(
        description=(
            "Why this answer is correct and others are wrong. "
            "Provides learning moment even for correct answers. "
            "2-3 sentences maximum."
        ),
        min_length=30,
        max_length=500,
    )

    @model_validator(mode="after")
    def validate_correct_answer(self) -> "QuizQuestion":
        """Validate that correct_answer is one of the options."""
        if self.correct_answer not in self.options:
            msg = f"correct_answer '{self.correct_answer}' must be one of {self.options}"
            raise ValueError(msg)
        return self


class Exercise(BaseModel):
    """Hands-on coding exercise with scaffolding and solution.

    Bridges theory to practice with guided implementation tasks.
    Includes difficulty rating for progressive skill building.
    """

    title: str = Field(
        description="Clear, action-oriented title (e.g., 'Build a Semantic Search API')",
        min_length=5,
        max_length=100,
    )
    difficulty: str = Field(
        description="Exercise difficulty level (same scale as CoreConcept.complexity_level)",
        pattern="^(Beginner|Intermediate|Advanced|Expert)$",
    )
    description: str = Field(
        description=(
            "What the learner will build and why. "
            "Include specific technologies and expected outcome. "
            "Example: 'Build a FastAPI endpoint that performs semantic search "
            "over 1000 documents using pgvector, returning top 10 results in <200ms.'"
        ),
        min_length=50,
        max_length=1000,
    )
    hints: list[str] = Field(
        description=(
            "Progressive hints that guide without spoiling. "
            "Order from high-level strategy to implementation details. "
            "3-5 hints maximum."
        ),
        min_length=3,
        max_length=5,
        default_factory=list,
    )
    solution: str = Field(
        description=(
            "Complete, working solution with explanatory comments. "
            "Should be copy-paste runnable. "
            "Optional field - exercises can omit solution for discovery learning."
        ),
        default="",
    )
    learning_objectives: list[str] = Field(
        description=(
            "Specific skills or concepts this exercise reinforces. "
            "Maps to CoreConcept entries for curriculum tracking. "
            "Example: 'Async database queries', 'Vector similarity search', 'API pagination'"
        ),
        min_length=2,
        max_length=5,
    )


class MermaidDiagram(BaseModel):
    """Mermaid.js diagram for visual explanation of architecture or flow.

    Supports multiple diagram types for different learning needs.
    Rendered by frontend and included in documentation.
    """

    title: str = Field(
        description="Descriptive title for the diagram (e.g., 'RAG Pipeline Data Flow')",
        min_length=5,
        max_length=100,
    )
    type: str = Field(
        description=(
            "Mermaid diagram type. "
            "Options: 'flowchart', 'sequence', 'class', 'state', 'er' (entity-relationship), 'gantt'. "
            "Choose based on what you're explaining (flow=process, sequence=interactions, class=structure)."
        ),
        pattern="^(flowchart|sequence|class|state|er|gantt)$",
    )
    mermaid_code: str = Field(
        description=(
            "Valid Mermaid.js syntax for the diagram. "
            "Must be syntactically correct - will be rendered directly. "
            "\n\n"
            "CRITICAL NODE LABEL CONSTRAINTS (prevents text truncation):\n"
            "- Diamond/decision nodes {label}: MAX 5 chars (e.g., {OK?}, {Yes}, {No})\n"
            "- Rectangle nodes [label]: MAX 15 chars per word, split long text\n"
            "- Use multi-word labels for clarity: [User Request] not [UserRequest]\n"
            "- For validation decisions: use {OK?} not {Valid?} or {Validation}\n"
            "- Keep terminal nodes concise: [Done], [Error], [End]\n"
            "\n"
            "Example:\n"
            "flowchart TD\n"
            "    A[User Query] --> B[Embed]\n"
            "    B --> C{OK?}\n"
            "    C -->|Yes| D[Search]\n"
            "    C -->|No| E[Error]"
        ),
        min_length=20,
    )
    description: str = Field(
        description=(
            "Text explanation of what the diagram shows. "
            "Provides accessibility and context. "
            "2-3 sentences."
        ),
        min_length=30,
        max_length=500,
    )


class SelfAssessment(BaseModel):
    """Self-assessment tools for learner progress tracking.

    Combines quiz questions with skill checklists for comprehensive evaluation.
    Used by tutor system to adapt lesson difficulty and recommend next steps.
    """

    quiz_questions: list[QuizQuestion] = Field(
        description=(
            "Multiple-choice or true/false questions testing key concepts. "
            "5-10 questions covering the full content scope. "
            "Mix difficulty levels for comprehensive assessment."
        ),
        min_length=5,
        max_length=10,
    )
    mastery_checklist: list[str] = Field(
        description=(
            "Skills the learner should be able to demonstrate after completing this content. "
            "Each item should be specific and testable. "
            "Example: 'Explain the trade-offs between semantic and keyword search', "
            "'Implement vector similarity search with <200ms latency', "
            "'Debug common pgvector configuration issues'"
        ),
        min_length=5,
        max_length=10,
    )


class GlossaryTerm(BaseModel):
    """Technical term definition for quick reference and search.

    Builds a searchable knowledge base and supports AI assistant context.
    Cross-references enable knowledge graph navigation.
    """

    term: str = Field(
        description="The technical term or acronym (e.g., 'RAG', 'pgvector', 'Embedding')",
        min_length=1,
        max_length=100,
    )
    definition: str = Field(
        description=(
            "Clear, concise definition (1-2 sentences). "
            "Avoid circular definitions - explain in simpler terms. "
            "Example: 'RAG (Retrieval Augmented Generation): A technique that enhances LLM "
            "responses by retrieving relevant context from a knowledge base before generating output.'"
        ),
        min_length=20,
        max_length=500,
    )
    see_also: list[str] = Field(
        description=(
            "Related terms for knowledge graph connections. "
            "Max 5 related terms that provide additional context. "
            "Example: 'Vector Embeddings', 'Semantic Search', 'LangChain'"
        ),
        max_length=5,
        default_factory=list,
    )


class Synthesis(BaseModel):
    """Synthesized insights from all agents."""

    technical_analysis: str = Field(
        description=(
            "Combined technical insights from all agents. "
            "Format as markdown with paragraphs separated by blank lines."
        )
    )
    implementation_guidance: str = Field(
        description=(
            "Unified implementation recommendations. "
            "Format as a markdown numbered list with each step on its own line. "
            "Example:\n1. First step\n2. Second step\n3. Third step"
        )
    )
    risk_assessment: str = Field(
        description=(
            "Consolidated risk analysis. Format as markdown with bullet points for each risk."
        )
    )
    recommendations: str = Field(
        description=(
            "Final recommendations prioritizing all perspectives. "
            "Format as markdown with bullet points for each recommendation."
        )
    )


class AggregatedInsights(BaseModel):
    """Aggregated insights from all agent findings.

    This schema defines the output structure for the aggregator node,
    which synthesizes findings from all 8 specialized agents into a
    cohesive, actionable narrative.

    Enhanced in v2.0 (Issue #302) to serve three audiences:
    1. AI Coding Assistants - Pre-formatted prompts, code snippets, file structure
    2. Tutor System - Core concepts, exercises, quizzes, learning objectives
    3. Human Readers - TLDR sections, glossary, visual diagrams
    """

    # Original fields (backward compatible)
    quick_reference: QuickReference | None = Field(
        description=(
            "Quick Reference section with critical information for fast scanning. "
            "Should be extracted from agent findings to front-load technology, "
            "complexity, commands, files, and common gotchas. "
            "Optional field - if extraction fails, template will skip this section."
        ),
        default=None,
    )
    executive_summary: str = Field(
        description=(
            "2-3 sentence summary of the entire analysis. "
            "Write as a cohesive paragraph, not a list."
        ),
        min_length=50,
    )
    key_findings: list[str] = Field(
        description=(
            "3-7 key findings prioritized by impact. "
            "Each finding should be a single concise sentence or phrase."
        ),
        min_length=3,
        max_length=7,
    )
    synthesis: Synthesis = Field(description="Synthesized insights from all agents")
    conflicts_resolved: list[ConflictResolution] = Field(
        description="List of conflicts that were detected and resolved",
        default_factory=list,
    )
    coverage_gaps: list[CoverageGap] = Field(
        description="Missing analysis perspectives when not all agents contribute",
        default_factory=list,
    )
    cross_domain_connections: list[CrossDomainConnection] = Field(
        description="Connections identified between different analysis domains",
        default_factory=list,
    )
    coverage_score: float = Field(
        description="Percentage of potential agents that contributed (0.0-1.0)",
        ge=0.0,
        le=1.0,
        default=0.0,
    )

    # NEW: Human Reader Enhancement (Issue #302)
    tldr: TLDRSection | None = Field(
        description=(
            "Executive summary optimized for human scanning (10-30 seconds). "
            "Provides immediate value assessment with key takeaways and time estimates. "
            "Optional - populated by aggregator when generating learning-oriented artifacts."
        ),
        default=None,
    )

    # NEW: Tutor System Support (Issue #302)
    core_concepts: list[CoreConcept] = Field(
        description=(
            "Fundamental concepts with pedagogical metadata. "
            "Used by tutor system for curriculum sequencing and knowledge graph building. "
            "Each concept includes complexity level, related topics, and learning context."
        ),
        default_factory=list,
    )
    exercises: list[Exercise] = Field(
        description=(
            "Hands-on coding exercises with progressive difficulty. "
            "Bridges theory to practice with hints, solutions, and learning objectives. "
            "Tutor system uses these to generate practice sessions."
        ),
        default_factory=list,
    )
    self_assessment: SelfAssessment | None = Field(
        description=(
            "Quiz questions and mastery checklist for progress tracking. "
            "Enables tutor system to validate understanding and adapt lesson difficulty. "
            "Optional - included when aggregator generates comprehensive learning artifacts."
        ),
        default=None,
    )

    # NEW: AI Assistant Optimization (Issue #302)
    ai_assistant_prompt: AIAssistantPrompt | None = Field(
        description=(
            "Pre-formatted context for AI coding assistants (Claude, Cursor, Copilot). "
            "Includes architectural context, implementation steps, code snippets, file structure. "
            "Optimized for one-shot code generation with high accuracy. "
            "Optional - populated when artifact contains actionable implementation guidance."
        ),
        default=None,
    )

    # NEW: Visual & Reference Materials (Issue #302)
    diagrams: list[MermaidDiagram] = Field(
        description=(
            "Mermaid.js diagrams for visual explanation (flowcharts, sequences, architecture). "
            "Supports multiple diagram types for different learning needs. "
            "Rendered by frontend and included in documentation exports."
        ),
        default_factory=list,
    )
    glossary: list[GlossaryTerm] = Field(
        description=(
            "Technical term definitions with cross-references. "
            "Builds searchable knowledge base and supports AI assistant context. "
            "Enables knowledge graph navigation through see_also links."
        ),
        default_factory=list,
    )
