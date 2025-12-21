"""Type definitions for tutor workflow state.

This module defines TypedDict structures for the TutorState fields,
providing type safety for LangGraph state management.
"""

from typing import TypedDict


class SyllabusLesson(TypedDict, total=False):
    """A single lesson within a syllabus section.

    Attributes:
        title: Lesson title
        description: Brief description of the lesson
        concepts: List of concepts covered
        duration_minutes: Estimated duration in minutes
        difficulty: Difficulty level (1-5)

    """

    title: str
    description: str
    concepts: list[str]
    duration_minutes: int
    difficulty: int


class SyllabusSection(TypedDict, total=False):
    """A section within a syllabus.

    Attributes:
        title: Section title
        description: Section overview
        lessons: List of lessons in this section
        prerequisites: List of prerequisite concept IDs
        learning_objectives: What user will learn

    """

    title: str
    description: str
    lessons: list[SyllabusLesson]
    prerequisites: list[str]
    learning_objectives: list[str]


class Syllabus(TypedDict, total=False):
    """Complete syllabus structure for tutoring.

    Attributes:
        title: Overall syllabus title
        description: High-level description
        sections: List of sections
        total_lessons: Total number of lessons
        estimated_hours: Estimated completion time
        target_level: Target skill level

    """

    title: str
    description: str
    sections: list[SyllabusSection]
    total_lessons: int
    estimated_hours: float
    target_level: str


class SessionMetadata(TypedDict, total=False):
    """Metadata for a tutoring session.

    Attributes:
        started_at: ISO timestamp when session started
        last_activity: ISO timestamp of last activity
        total_messages: Total messages exchanged
        topics_covered: List of topics covered
        completion_percentage: Overall completion (0-100)

    """

    started_at: str
    last_activity: str
    total_messages: int
    topics_covered: list[str]
    completion_percentage: float
