"""Comprehensive unit tests for aggregated_insights schema.

Tests all Pydantic models with focus on:
- Field validation and constraints
- Model validators (especially QuizQuestion.validate_correct_answer)
- Valid/invalid input scenarios
- Edge cases and boundary conditions
- Nested model validation
"""

import pytest
from pydantic import ValidationError

from app.domains.analysis.workflows.tasks.schemas.aggregated_insights import (

@pytest.mark.unit
    AggregatedInsights,
    AIAssistantPrompt,
    ConflictResolution,
    CoreConcept,
    CoverageGap,
    CrossDomainConnection,
    Exercise,
    GlossaryTerm,
    GotchaItem,
    MermaidDiagram,
    QuickReference,
    QuizQuestion,
    SelfAssessment,
    Synthesis,
    TLDRSection,
)

# ============================================================================
# QuizQuestion Tests (Priority - has validator)
# ============================================================================


class TestQuizQuestion:
    """Tests for QuizQuestion model with correct_answer validator."""

    def test_valid_quiz_question(self):
        """Test creating a valid quiz question."""
        quiz = QuizQuestion(
            question="What is semantic chunking?",
            options=[
                "Fixed-size text splitting",
                "Content-aware text splitting",
                "Random text splitting",
            ],
            correct_answer="Content-aware text splitting",
            explanation="Semantic chunking analyzes content meaning to determine optimal split points, "
            "improving retrieval accuracy.",
        )

        assert quiz.question == "What is semantic chunking?"
        assert len(quiz.options) == 3
        assert quiz.correct_answer in quiz.options
        assert len(quiz.explanation) >= 30

    def test_correct_answer_must_be_in_options(self):
        """Test that correct_answer validator enforces option membership."""
        with pytest.raises(ValidationError) as exc_info:
            QuizQuestion(
                question="What is RAG?",
                options=["Retrieval", "Generation", "Augmentation"],
                correct_answer="Retrieval Augmented Generation",  # Not in options
                explanation="RAG combines retrieval with generation for better responses.",
            )

        # The validator raises a ValueError which becomes a ValidationError
        error_msg = str(exc_info.value)
        assert "must be one of" in error_msg

    def test_invalid_correct_answer_raises_value_error(self):
        """Test that incorrect correct_answer raises ValueError via validator."""
        with pytest.raises(ValidationError) as exc_info:
            QuizQuestion(
                question="Which is faster?",
                options=["Option A", "Option B"],
                correct_answer="Option C",  # Not in options
                explanation="This explanation has sufficient length to pass validation.",
            )

        # Check that the validation error message contains expected info
        error_msg = str(exc_info.value)
        assert "Option C" in error_msg and "must be one of" in error_msg

    @pytest.mark.parametrize(
        ("question", "should_pass"),
        [
            ("What?", False),  # Too short (min_length=10)
            ("What is this?", True),  # Valid length
            ("a" * 301, False),  # Too long (max_length=300)
            ("a" * 300, True),  # Exactly max length
        ],
    )
    def test_question_length_constraints(self, question, should_pass):
        """Test question field length constraints."""
        if should_pass:
            quiz = QuizQuestion(
                question=question,
                options=["True", "False"],
                correct_answer="True",
                explanation="This validates question length constraints.",
            )
            assert quiz.question == question
        else:
            with pytest.raises(ValidationError):
                QuizQuestion(
                    question=question,
                    options=["True", "False"],
                    correct_answer="True",
                    explanation="This should fail validation.",
                )

    @pytest.mark.parametrize(
        ("options", "should_pass"),
        [
            (["A"], False),  # Too few (min_length=2)
            (["A", "B"], True),  # Minimum valid
            (["A", "B", "C", "D", "E"], True),  # Maximum valid
            (["A", "B", "C", "D", "E", "F"], False),  # Too many (max_length=5)
        ],
    )
    def test_options_count_constraints(self, options, should_pass):
        """Test options field count constraints (2-5)."""
        if should_pass:
            quiz = QuizQuestion(
                question="Test question?",
                options=options,
                correct_answer=options[0],
                explanation="This validates options count constraints.",
            )
            assert len(quiz.options) == len(options)
        else:
            with pytest.raises(ValidationError):
                QuizQuestion(
                    question="Test question?",
                    options=options,
                    correct_answer=options[0] if options else "A",
                    explanation="This should fail validation.",
                )

    def test_true_false_question(self):
        """Test creating a true/false quiz question."""
        quiz = QuizQuestion(
            question="Is semantic chunking better than fixed-size chunking?",
            options=["True", "False"],
            correct_answer="True",
            explanation="Semantic chunking improves retrieval accuracy by 40% compared to fixed-size chunks.",
        )

        assert len(quiz.options) == 2
        assert "True" in quiz.options
        assert "False" in quiz.options
        assert quiz.correct_answer == "True"

    def test_explanation_length_constraints(self):
        """Test explanation field length constraints."""
        # Too short
        with pytest.raises(ValidationError):
            QuizQuestion(
                question="Test question?",
                options=["A", "B"],
                correct_answer="A",
                explanation="Too short",  # Less than 30 chars
            )

        # Valid
        quiz = QuizQuestion(
            question="Test question?",
            options=["A", "B"],
            correct_answer="A",
            explanation="This is a valid explanation with at least 30 characters.",
        )
        assert len(quiz.explanation) >= 30

        # Too long
        with pytest.raises(ValidationError):
            QuizQuestion(
                question="Test question?",
                options=["A", "B"],
                correct_answer="A",
                explanation="a" * 501,  # More than 500 chars
            )


# ============================================================================
# TLDRSection Tests
# ============================================================================


class TestTLDRSection:
    """Tests for TLDRSection model."""

    def test_valid_tldr_section(self):
        """Test creating a valid TLDR section."""
        tldr = TLDRSection(
            summary="This guide teaches vector database optimization for RAG systems. "
            "You will learn how to reduce latency by 60% through proper indexing strategies.",
            key_takeaways=[
                "Build a production-ready RAG pipeline with <200ms query latency",
                "Implement semantic chunking for 40% better retrieval accuracy",
                "Configure pgvector for optimal performance",
            ],
            time_to_implement="4-6 hours (2h setup, 2h implementation, 1-2h testing)",
        )

        assert len(tldr.summary) >= 50
        assert len(tldr.key_takeaways) == 3
        assert "4-6 hours" in tldr.time_to_implement

    def test_summary_length_constraints(self):
        """Test summary field length constraints."""
        # Too short
        with pytest.raises(ValidationError):
            TLDRSection(
                summary="Short",  # Less than 50 chars
                key_takeaways=["A", "B", "C"],
                time_to_implement="4-6 hours",
            )

        # Too long
        with pytest.raises(ValidationError):
            TLDRSection(
                summary="a" * 501,  # More than 500 chars
                key_takeaways=["A", "B", "C"],
                time_to_implement="4-6 hours",
            )

    @pytest.mark.parametrize(
        ("takeaways", "should_pass"),
        [
            (["A", "B"], False),  # Too few (min_length=3)
            (["A", "B", "C"], True),  # Minimum valid
            (["A", "B", "C", "D", "E"], True),  # Maximum valid
            (["A", "B", "C", "D", "E", "F"], False),  # Too many (max_length=5)
        ],
    )
    def test_key_takeaways_count_constraints(self, takeaways, should_pass):
        """Test key_takeaways field count constraints (3-5)."""
        if should_pass:
            tldr = TLDRSection(
                summary="This is a valid summary with more than 50 characters to pass validation.",
                key_takeaways=takeaways,
                time_to_implement="4-6 hours total",  # min_length=10
            )
            assert len(tldr.key_takeaways) == len(takeaways)
        else:
            with pytest.raises(ValidationError):
                TLDRSection(
                    summary="This is a valid summary with more than 50 characters to pass validation.",
                    key_takeaways=takeaways,
                    time_to_implement="4-6 hours total",  # min_length=10
                )


# ============================================================================
# CoreConcept Tests
# ============================================================================


class TestCoreConcept:
    """Tests for CoreConcept model."""

    def test_valid_core_concept(self):
        """Test creating a valid core concept."""
        concept = CoreConcept(
            name="Semantic Chunking",
            definition="A technique that analyzes content meaning to determine optimal split points, "
            "improving retrieval accuracy.",
            why_it_matters="Improves retrieval accuracy by 40% compared to fixed-size chunks.",
            related_concepts=["Vector Embeddings", "Cosine Similarity"],
            complexity_level="Intermediate",
        )

        assert concept.name == "Semantic Chunking"
        assert len(concept.definition) >= 50
        assert len(concept.why_it_matters) >= 30
        assert concept.complexity_level == "Intermediate"

    @pytest.mark.parametrize(
        "complexity_level",
        ["Beginner", "Intermediate", "Advanced", "Expert"],
    )
    def test_valid_complexity_levels(self, complexity_level):
        """Test all valid complexity level patterns."""
        concept = CoreConcept(
            name="Test Concept",
            definition="This is a valid definition with more than 50 characters to pass validation.",
            why_it_matters="This explains why it matters with sufficient length.",
            complexity_level=complexity_level,
        )
        assert concept.complexity_level == complexity_level

    def test_invalid_complexity_level(self):
        """Test that invalid complexity level raises ValidationError."""
        with pytest.raises(ValidationError):
            CoreConcept(
                name="Test Concept",
                definition="This is a valid definition with more than 50 characters to pass validation.",
                why_it_matters="This explains why it matters with sufficient length.",
                complexity_level="Master",  # Invalid
            )

    def test_optional_related_concepts(self):
        """Test that related_concepts is optional."""
        concept = CoreConcept(
            name="Test Concept",
            definition="This is a valid definition with more than 50 characters to pass validation.",
            why_it_matters="This explains why it matters with sufficient length.",
            complexity_level="Beginner",
        )
        assert concept.related_concepts == []

    def test_related_concepts_max_length(self):
        """Test related_concepts max length constraint."""
        # Valid - exactly 5
        concept = CoreConcept(
            name="Test Concept",
            definition="This is a valid definition with more than 50 characters to pass validation.",
            why_it_matters="This explains why it matters with sufficient length.",
            complexity_level="Beginner",
            related_concepts=["A", "B", "C", "D", "E"],
        )
        assert len(concept.related_concepts) == 5

        # Invalid - more than 5
        with pytest.raises(ValidationError):
            CoreConcept(
                name="Test Concept",
                definition="This is a valid definition with more than 50 characters to pass validation.",
                why_it_matters="This explains why it matters with sufficient length.",
                complexity_level="Beginner",
                related_concepts=["A", "B", "C", "D", "E", "F"],
            )


# ============================================================================
# Exercise Tests
# ============================================================================


class TestExercise:
    """Tests for Exercise model."""

    def test_valid_exercise(self):
        """Test creating a valid exercise."""
        exercise = Exercise(
            title="Build a Semantic Search API",
            difficulty="Intermediate",
            description="Build a FastAPI endpoint that performs semantic search over 1000 documents "
            "using pgvector, returning top 10 results in <200ms.",
            hints=[
                "Start with database connection setup",
                "Create embedding function",
                "Implement vector similarity search",
            ],
            solution="# Complete solution code here",
            learning_objectives=["Async database queries", "Vector similarity search"],
        )

        assert exercise.title == "Build a Semantic Search API"
        assert exercise.difficulty == "Intermediate"
        assert len(exercise.hints) == 3
        assert len(exercise.learning_objectives) == 2

    @pytest.mark.parametrize(
        "difficulty",
        ["Beginner", "Intermediate", "Advanced", "Expert"],
    )
    def test_valid_difficulty_levels(self, difficulty):
        """Test all valid difficulty patterns."""
        exercise = Exercise(
            title="Test Exercise",
            difficulty=difficulty,
            description="This is a valid description with more than 50 characters to pass validation.",
            learning_objectives=["Objective 1", "Objective 2"],
        )
        assert exercise.difficulty == difficulty

    def test_optional_hints_and_solution(self):
        """Test that hints and solution are optional."""
        exercise = Exercise(
            title="Test Exercise",
            difficulty="Beginner",
            description="This is a valid description with more than 50 characters to pass validation.",
            learning_objectives=["Objective 1", "Objective 2"],
        )
        assert exercise.hints == []
        assert exercise.solution == ""

    def test_learning_objectives_constraints(self):
        """Test learning_objectives count constraints (2-5)."""
        # Too few
        with pytest.raises(ValidationError):
            Exercise(
                title="Test Exercise",
                difficulty="Beginner",
                description="This is a valid description with more than 50 characters to pass validation.",
                learning_objectives=["Only one"],
            )

        # Valid
        exercise = Exercise(
            title="Test Exercise",
            difficulty="Beginner",
            description="This is a valid description with more than 50 characters to pass validation.",
            learning_objectives=["Objective 1", "Objective 2"],
        )
        assert len(exercise.learning_objectives) == 2

        # Too many
        with pytest.raises(ValidationError):
            Exercise(
                title="Test Exercise",
                difficulty="Beginner",
                description="This is a valid description with more than 50 characters to pass validation.",
                learning_objectives=["A", "B", "C", "D", "E", "F"],
            )


# ============================================================================
# GlossaryTerm Tests
# ============================================================================


class TestGlossaryTerm:
    """Tests for GlossaryTerm model."""

    def test_valid_glossary_term(self):
        """Test creating a valid glossary term."""
        term = GlossaryTerm(
            term="RAG",
            definition="Retrieval Augmented Generation: A technique that enhances LLM responses "
            "by retrieving relevant context from a knowledge base.",
            see_also=["Vector Embeddings", "Semantic Search"],
        )

        assert term.term == "RAG"
        assert len(term.definition) >= 20
        assert len(term.see_also) == 2

    def test_optional_see_also(self):
        """Test that see_also is optional."""
        term = GlossaryTerm(
            term="Vector",
            definition="A mathematical representation of text as numerical arrays.",
        )
        assert term.see_also == []

    def test_see_also_max_length(self):
        """Test see_also max length constraint."""
        # Valid
        term = GlossaryTerm(
            term="Test",
            definition="A test definition with sufficient length.",
            see_also=["A", "B", "C", "D", "E"],
        )
        assert len(term.see_also) == 5

        # Invalid - too many
        with pytest.raises(ValidationError):
            GlossaryTerm(
                term="Test",
                definition="A test definition with sufficient length.",
                see_also=["A", "B", "C", "D", "E", "F"],
            )


# ============================================================================
# AIAssistantPrompt Tests
# ============================================================================


class TestAIAssistantPrompt:
    """Tests for AIAssistantPrompt model."""

    def test_valid_ai_assistant_prompt(self):
        """Test creating a valid AI assistant prompt."""
        prompt = AIAssistantPrompt(
            context="This RAG pipeline runs in a FastAPI async endpoint, querying PostgreSQL "
            "with pgvector extension.",
            implementation_steps=[
                "Install dependencies",
                "Configure database",
                "Create models",
                "Implement endpoints",
                "Add tests",
            ],
            code_snippets={
                "vector_search": "SELECT * FROM embeddings ORDER BY embedding <=> $1 LIMIT 10"
            },
            file_structure={"app/services/rag.py": "RAG service implementation"},
            success_criteria=[
                "Query latency <200ms",
                "Recall@10 >0.85",
                "All tests passing",
            ],
        )

        assert len(prompt.context) >= 50
        assert len(prompt.implementation_steps) == 5
        assert "vector_search" in prompt.code_snippets
        assert len(prompt.success_criteria) == 3

    def test_implementation_steps_constraints(self):
        """Test implementation_steps count constraints (5-10)."""
        # Too few
        with pytest.raises(ValidationError):
            AIAssistantPrompt(
                context="Valid context with more than 50 characters to pass validation.",
                implementation_steps=["Step 1", "Step 2", "Step 3", "Step 4"],
                success_criteria=["Criterion 1", "Criterion 2", "Criterion 3"],
            )

        # Valid minimum
        prompt = AIAssistantPrompt(
            context="Valid context with more than 50 characters to pass validation.",
            implementation_steps=["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"],
            success_criteria=["Criterion 1", "Criterion 2", "Criterion 3"],
        )
        assert len(prompt.implementation_steps) == 5

        # Valid maximum
        prompt = AIAssistantPrompt(
            context="Valid context with more than 50 characters to pass validation.",
            implementation_steps=[f"Step {i}" for i in range(1, 11)],
            success_criteria=["Criterion 1", "Criterion 2", "Criterion 3"],
        )
        assert len(prompt.implementation_steps) == 10

        # Too many
        with pytest.raises(ValidationError):
            AIAssistantPrompt(
                context="Valid context with more than 50 characters to pass validation.",
                implementation_steps=[f"Step {i}" for i in range(1, 12)],
                success_criteria=["Criterion 1", "Criterion 2", "Criterion 3"],
            )

    def test_optional_code_snippets_and_file_structure(self):
        """Test that code_snippets and file_structure are optional."""
        prompt = AIAssistantPrompt(
            context="Valid context with more than 50 characters to pass validation.",
            implementation_steps=["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"],
            success_criteria=["Criterion 1", "Criterion 2", "Criterion 3"],
        )
        assert prompt.code_snippets == {}
        assert prompt.file_structure == {}


# ============================================================================
# QuickReference Tests
# ============================================================================


class TestQuickReference:
    """Tests for QuickReference model."""

    def test_valid_quick_reference(self):
        """Test creating a valid quick reference."""
        ref = QuickReference(
            primary_technology="LangGraph 0.6.7 + PostgreSQL 14",
            complexity="Intermediate (Est. 3-4 hours)",
            prerequisites=["Python 3.11+", "PostgreSQL 14+", "Docker installed"],
            critical_commands=["pip install langgraph==0.6.7", "docker-compose up -d"],
            files_to_modify=["app/workflows/graph.py", "app/models/state.py"],
            gotchas=[
                GotchaItem(
                    issue="Circular imports between modules",
                    symptom="ImportError: cannot import name X from Y",
                    quick_fix="Use TYPE_CHECKING import guard",
                )
            ],
        )

        assert "LangGraph" in ref.primary_technology
        assert "3-4 hours" in ref.complexity
        assert len(ref.prerequisites) == 3
        assert len(ref.gotchas) == 1

    def test_prerequisites_max_length(self):
        """Test prerequisites max length constraint."""
        # Valid
        ref = QuickReference(
            primary_technology="React 19 + Next.js 15",
            complexity="Beginner (Est. 1-2 hours)",
            prerequisites=["A", "B", "C", "D"],
            critical_commands=["npm install"],
        )
        assert len(ref.prerequisites) == 4

        # Invalid - too many
        with pytest.raises(ValidationError):
            QuickReference(
                primary_technology="React 19 + Next.js 15",
                complexity="Beginner (Est. 1-2 hours)",
                prerequisites=["A", "B", "C", "D", "E"],
                critical_commands=["npm install"],
            )

    def test_optional_fields(self):
        """Test that files_to_modify and gotchas are optional."""
        ref = QuickReference(
            primary_technology="React 19",
            complexity="Beginner (Est. 1-2 hours)",
            prerequisites=["Node.js 18+"],
            critical_commands=["npm install"],
        )
        assert ref.files_to_modify == []
        assert ref.gotchas == []


# ============================================================================
# SelfAssessment Tests
# ============================================================================


class TestSelfAssessment:
    """Tests for SelfAssessment model."""

    def test_valid_self_assessment(self):
        """Test creating a valid self assessment."""
        assessment = SelfAssessment(
            quiz_questions=[
                QuizQuestion(
                    question=f"Question {i}?",
                    options=["True", "False"],
                    correct_answer="True",
                    explanation="This is a valid explanation with sufficient length.",
                )
                for i in range(1, 6)
            ],
            mastery_checklist=[
                "Skill 1",
                "Skill 2",
                "Skill 3",
                "Skill 4",
                "Skill 5",
            ],
        )

        assert len(assessment.quiz_questions) == 5
        assert len(assessment.mastery_checklist) == 5

    def test_quiz_questions_constraints(self):
        """Test quiz_questions count constraints (5-10)."""
        # Too few
        with pytest.raises(ValidationError):
            SelfAssessment(
                quiz_questions=[
                    QuizQuestion(
                        question="Question?",
                        options=["True", "False"],
                        correct_answer="True",
                        explanation="Valid explanation.",
                    )
                    for _ in range(4)
                ],
                mastery_checklist=["Skill 1", "Skill 2", "Skill 3", "Skill 4", "Skill 5"],
            )

        # Valid maximum
        assessment = SelfAssessment(
            quiz_questions=[
                QuizQuestion(
                    question=f"Question {i}?",
                    options=["True", "False"],
                    correct_answer="True",
                    explanation="Valid explanation with sufficient length.",
                )
                for i in range(1, 11)
            ],
            mastery_checklist=["Skill 1", "Skill 2", "Skill 3", "Skill 4", "Skill 5"],
        )
        assert len(assessment.quiz_questions) == 10


# ============================================================================
# MermaidDiagram Tests
# ============================================================================


class TestMermaidDiagram:
    """Tests for MermaidDiagram model."""

    def test_valid_mermaid_diagram(self):
        """Test creating a valid mermaid diagram."""
        diagram = MermaidDiagram(
            title="RAG Pipeline Data Flow",
            type="flowchart",
            mermaid_code="flowchart TD\n    A[User Query] --> B[Embedding Model]\n    B --> C[Vector Search]",
            description="This diagram shows the data flow through the RAG pipeline.",
        )

        assert diagram.title == "RAG Pipeline Data Flow"
        assert diagram.type == "flowchart"
        assert "flowchart TD" in diagram.mermaid_code

    @pytest.mark.parametrize(
        "diagram_type",
        ["flowchart", "sequence", "class", "state", "er", "gantt"],
    )
    def test_valid_diagram_types(self, diagram_type):
        """Test all valid diagram type patterns."""
        diagram = MermaidDiagram(
            title="Test Diagram",
            type=diagram_type,
            mermaid_code="graph TD\n    A --> B",
            description="This is a test diagram with sufficient description.",
        )
        assert diagram.type == diagram_type

    def test_invalid_diagram_type(self):
        """Test that invalid diagram type raises ValidationError."""
        with pytest.raises(ValidationError):
            MermaidDiagram(
                title="Test Diagram",
                type="invalid",  # Not a valid type
                mermaid_code="graph TD\n    A --> B",
                description="This is a test diagram.",
            )


# ============================================================================
# Nested Model Tests
# ============================================================================


class TestNestedModels:
    """Tests for models with nested structures."""

    def test_conflict_resolution(self):
        """Test ConflictResolution model."""
        conflict = ConflictResolution(
            conflict="Security vs Performance trade-off",
            resolution="Prioritize security with minimal performance impact",
            priority_agent="security_auditor",
            reasoning="Security vulnerabilities cannot be compromised",
        )
        assert conflict.priority_agent == "security_auditor"

    def test_coverage_gap(self):
        """Test CoverageGap model."""
        gap = CoverageGap(
            missing_agent="cost_optimizer",
            missing_perspective="Cost analysis for cloud deployment",
            impact="Unknown budget requirements",
        )
        assert gap.missing_agent == "cost_optimizer"

    def test_cross_domain_connection(self):
        """Test CrossDomainConnection model."""
        connection = CrossDomainConnection(
            domains=["security", "performance"],
            connection="Encryption adds latency overhead",
            agents_involved=["security_auditor", "performance_tester"],
        )
        assert len(connection.domains) == 2
        assert len(connection.agents_involved) == 2

    def test_cross_domain_connection_domains_exactly_two(self):
        """Test that domains must have exactly 2 items."""
        # Too few
        with pytest.raises(ValidationError):
            CrossDomainConnection(
                domains=["security"],
                connection="Test",
                agents_involved=["agent1", "agent2"],
            )

        # Too many
        with pytest.raises(ValidationError):
            CrossDomainConnection(
                domains=["security", "performance", "cost"],
                connection="Test",
                agents_involved=["agent1", "agent2"],
            )

    def test_synthesis(self):
        """Test Synthesis model."""
        synthesis = Synthesis(
            technical_analysis="Comprehensive technical analysis here.",
            implementation_guidance="1. Step one\n2. Step two\n3. Step three",
            risk_assessment="- Risk 1\n- Risk 2",
            recommendations="- Recommendation 1\n- Recommendation 2",
        )
        assert "technical analysis" in synthesis.technical_analysis
        assert "Step one" in synthesis.implementation_guidance

    def test_gotcha_item(self):
        """Test GotchaItem model."""
        gotcha = GotchaItem(
            issue="Circular imports",
            symptom="ImportError during module loading",
            quick_fix="Use TYPE_CHECKING guards",
        )
        assert gotcha.issue == "Circular imports"


# ============================================================================
# AggregatedInsights Full Model Tests
# ============================================================================


class TestAggregatedInsights:
    """Tests for the full AggregatedInsights model."""

    def test_minimal_valid_aggregated_insights(self):
        """Test creating AggregatedInsights with minimal required fields."""
        insights = AggregatedInsights(
            executive_summary="This is a comprehensive analysis of the technical content "
            "providing actionable insights.",
            key_findings=[
                "Finding 1",
                "Finding 2",
                "Finding 3",
            ],
            synthesis=Synthesis(
                technical_analysis="Technical analysis content.",
                implementation_guidance="1. Step one\n2. Step two",
                risk_assessment="- Risk 1",
                recommendations="- Recommendation 1",
            ),
        )

        assert len(insights.executive_summary) >= 50
        assert len(insights.key_findings) == 3
        assert insights.coverage_score == 0.0
        assert insights.conflicts_resolved == []

    def test_full_aggregated_insights(self):
        """Test creating AggregatedInsights with all fields populated."""
        insights = AggregatedInsights(
            quick_reference=QuickReference(
                primary_technology="LangGraph 0.6.7",
                complexity="Intermediate (Est. 3-4 hours)",
                prerequisites=["Python 3.11+"],
                critical_commands=["pip install langgraph"],
            ),
            executive_summary="Comprehensive analysis of RAG implementation with LangGraph "
            "and pgvector.",
            key_findings=[
                "High performance achievable",
                "Security considerations important",
                "Moderate complexity",
            ],
            synthesis=Synthesis(
                technical_analysis="Detailed technical analysis.",
                implementation_guidance="1. Setup\n2. Implement\n3. Test",
                risk_assessment="- Risk 1\n- Risk 2",
                recommendations="- Use async patterns\n- Add monitoring",
            ),
            conflicts_resolved=[
                ConflictResolution(
                    conflict="Performance vs Security",
                    resolution="Balance both",
                    priority_agent="security_auditor",
                    reasoning="Security is critical",
                )
            ],
            coverage_gaps=[],
            cross_domain_connections=[],
            coverage_score=0.875,
            tldr=TLDRSection(
                summary="Learn RAG optimization techniques for production systems with "
                "proven performance improvements.",
                key_takeaways=[
                    "Build production RAG",
                    "Optimize performance",
                    "Implement security",
                ],
                time_to_implement="4-6 hours (2h setup, 2h implementation, 2h testing)",
            ),
            core_concepts=[
                CoreConcept(
                    name="Vector Search",
                    definition="Semantic similarity search using vector embeddings to find "
                    "relevant content.",
                    why_it_matters="Improves retrieval accuracy significantly.",
                    complexity_level="Intermediate",
                )
            ],
            exercises=[
                Exercise(
                    title="Build RAG API",
                    difficulty="Intermediate",
                    description="Create a FastAPI endpoint with semantic search using pgvector "
                    "for production use.",
                    learning_objectives=["API design", "Vector search"],
                )
            ],
            self_assessment=SelfAssessment(
                quiz_questions=[
                    QuizQuestion(
                        question=f"Test question {i}?",
                        options=["True", "False"],
                        correct_answer="True",
                        explanation="Explanation for the correct answer.",
                    )
                    for i in range(1, 6)
                ],
                mastery_checklist=[
                    "Skill 1",
                    "Skill 2",
                    "Skill 3",
                    "Skill 4",
                    "Skill 5",
                ],
            ),
            ai_assistant_prompt=AIAssistantPrompt(
                context="FastAPI with PostgreSQL and pgvector for semantic search implementation.",
                implementation_steps=[
                    "Install dependencies",
                    "Setup database",
                    "Create models",
                    "Implement endpoints",
                    "Add tests",
                ],
                success_criteria=[
                    "Tests passing",
                    "Latency <200ms",
                    "Accuracy >85%",
                ],
            ),
            diagrams=[
                MermaidDiagram(
                    title="RAG Flow",
                    type="flowchart",
                    mermaid_code="flowchart TD\n    A[Query] --> B[Embedding]",
                    description="Shows the RAG pipeline data flow.",
                )
            ],
            glossary=[
                GlossaryTerm(
                    term="RAG",
                    definition="Retrieval Augmented Generation for enhanced LLM responses.",
                )
            ],
        )

        assert insights.quick_reference is not None
        assert insights.tldr is not None
        assert len(insights.core_concepts) == 1
        assert len(insights.exercises) == 1
        assert insights.self_assessment is not None
        assert insights.ai_assistant_prompt is not None
        assert len(insights.diagrams) == 1
        assert len(insights.glossary) == 1
        assert 0.0 <= insights.coverage_score <= 1.0

    def test_optional_enhanced_fields(self):
        """Test that all v2.0 enhancement fields are optional."""
        insights = AggregatedInsights(
            executive_summary="Basic analysis with minimal fields for backward compatibility.",
            key_findings=["Finding 1", "Finding 2", "Finding 3"],
            synthesis=Synthesis(
                technical_analysis="Analysis.",
                implementation_guidance="1. Step",
                risk_assessment="Risk",
                recommendations="Recommendation",
            ),
        )

        # All new fields should have default values
        assert insights.quick_reference is None
        assert insights.tldr is None
        assert insights.core_concepts == []
        assert insights.exercises == []
        assert insights.self_assessment is None
        assert insights.ai_assistant_prompt is None
        assert insights.diagrams == []
        assert insights.glossary == []

    def test_coverage_score_bounds(self):
        """Test coverage_score must be between 0.0 and 1.0."""
        # Valid - minimum
        insights = AggregatedInsights(
            executive_summary="This is a comprehensive analysis of technical content providing insights.",
            key_findings=["A", "B", "C"],
            synthesis=Synthesis(
                technical_analysis="Analysis",
                implementation_guidance="Guidance",
                risk_assessment="Risk",
                recommendations="Recommendations",
            ),
            coverage_score=0.0,
        )
        assert insights.coverage_score == 0.0

        # Valid - maximum
        insights = AggregatedInsights(
            executive_summary="This is a comprehensive analysis of technical content providing insights.",
            key_findings=["A", "B", "C"],
            synthesis=Synthesis(
                technical_analysis="Analysis",
                implementation_guidance="Guidance",
                risk_assessment="Risk",
                recommendations="Recommendations",
            ),
            coverage_score=1.0,
        )
        assert insights.coverage_score == 1.0

        # Invalid - below minimum
        with pytest.raises(ValidationError):
            AggregatedInsights(
                executive_summary="This is a comprehensive analysis of technical content providing insights.",
                key_findings=["A", "B", "C"],
                synthesis=Synthesis(
                    technical_analysis="Analysis",
                    implementation_guidance="Guidance",
                    risk_assessment="Risk",
                    recommendations="Recommendations",
                ),
                coverage_score=-0.1,
            )

        # Invalid - above maximum
        with pytest.raises(ValidationError):
            AggregatedInsights(
                executive_summary="This is a comprehensive analysis of technical content providing insights.",
                key_findings=["A", "B", "C"],
                synthesis=Synthesis(
                    technical_analysis="Analysis",
                    implementation_guidance="Guidance",
                    risk_assessment="Risk",
                    recommendations="Recommendations",
                ),
                coverage_score=1.1,
            )
