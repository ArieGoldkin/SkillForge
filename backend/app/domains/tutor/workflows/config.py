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

# Tutor prompt names (Issue #414: Migrated to Jinja2 templates)
PROMPT_SYLLABUS_GENERATION = "tutor-syllabus-generation"
PROMPT_LESSON_DELIVERY = "tutor-lesson-delivery"
PROMPT_SOCRATIC_QUESTION = "tutor-socratic-question"
PROMPT_READINESS_ASSESSMENT = "tutor-readiness-assessment"

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
