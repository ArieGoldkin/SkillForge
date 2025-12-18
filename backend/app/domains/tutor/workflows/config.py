"""Configuration constants for tutor workflow."""

from app.domains.analysis.services.context.compaction import CompactionConfig

# Syllabus generation settings
SYLLABUS_MIN_SECTIONS = 2
SYLLABUS_MAX_SECTIONS = 4
SYLLABUS_MIN_LESSONS_PER_SECTION = 2
SYLLABUS_MAX_LESSONS_PER_SECTION = 3

# Context management settings
SLIDING_WINDOW_SIZE = 10  # Last N messages kept verbatim
TOKEN_BUDGET = 6000  # Max tokens for context (~6000 tokens)
SUMMARY_THRESHOLD = 20  # Summarize if more than N messages

# Assessment settings
MAX_ATTEMPTS_PER_LESSON = 3  # Max attempts before moving on
READINESS_CONFIDENCE_THRESHOLD = 0.7  # Minimum confidence to mark ready

# Streaming settings
STREAMING_CHUNK_SIZE = 50  # Characters per chunk for SSE streaming

# Tutor prompts (will be moved to tasks module in Phase 2)
SYLLABUS_GENERATION_PROMPT = (
    "Generate a personalized curriculum for teaching the following content.\n\n"
    "Content Summary:\n"
    "{analysis_summary}\n\n"
    "User Level: {user_level}\n\n"
    "Create a curriculum with 2-4 sections, each containing 2-3 lessons.\n"
    "Each lesson should cover one key concept with:\n"
    "- Clear explanation\n"
    "- Analogical explanation (if helpful)\n"
    "- Concrete example\n"
    "- Practice exercise/question\n\n"
    "Return as JSON matching the Syllabus schema."
)

LESSON_DELIVERY_PROMPT = """Deliver a lesson on the following concept:

Concept: {concept}
Section: {section_title}
Lesson: {lesson_title}

User Level: {user_level}
Previous Understanding: {understanding_scores}

Provide:
1. Clear explanation of the concept
2. An analogy to help understanding
3. A concrete example
4. A practice exercise or question

Adapt the complexity based on the user's level."""

SOCRATIC_QUESTION_PROMPT = """Generate a Socratic question based on the lesson and user's response.

Lesson Concept: {concept}
User Response: {user_response}
User Level: {user_level}

Generate a question that:
- For beginners: Checks understanding before explanation
- For intermediate/advanced: Challenges thinking after explanation
- Guides the user to discover the answer themselves
- Is contextual to the current lesson

Return a single thoughtful question."""

READINESS_ASSESSMENT_PROMPT = """Assess the user's understanding based on their response.

Lesson Concept: {concept}
User Response: {user_response}
Previous Understanding: {understanding_scores}

Evaluate:
1. Does the user demonstrate understanding? (boolean)
2. Confidence in assessment (0.0-1.0)
3. Reasoning for the assessment
4. Suggested action: 'rephrase' if not ready, 'move_on' if ready

Return as JSON matching ReadinessAssessment schema."""

TUTOR_CONFIG = {
    "syllabus": {
        "min_sections": SYLLABUS_MIN_SECTIONS,
        "max_sections": SYLLABUS_MAX_SECTIONS,
        "min_lessons_per_section": SYLLABUS_MIN_LESSONS_PER_SECTION,
        "max_lessons_per_section": SYLLABUS_MAX_LESSONS_PER_SECTION,
    },
    "context": {
        "sliding_window_size": SLIDING_WINDOW_SIZE,
        "token_budget": TOKEN_BUDGET,
        "summary_threshold": SUMMARY_THRESHOLD,
    },
    "assessment": {
        "max_attempts_per_lesson": MAX_ATTEMPTS_PER_LESSON,
        "readiness_confidence_threshold": READINESS_CONFIDENCE_THRESHOLD,
    },
    "streaming": {
        "chunk_size": STREAMING_CHUNK_SIZE,
    },
}

# Tutor-specific compaction config (Issue #270)
TUTOR_COMPACTION_CONFIG = CompactionConfig(
    max_turns_full=5,  # Keep last 5 turns verbatim
    summarize_after=10,  # Summarize after 10 turns
    summary_max_tokens=500,  # Limit summary length
    preserve_tool_calls=True,
    token_budget=6000,
)
