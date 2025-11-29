"""Syllabus schemas for tutor workflow."""

from pydantic import BaseModel, Field


class Lesson(BaseModel):
    """Lesson in a section.

    Attributes:
        title: Lesson title
        concept: Main concept being taught
        explanation: Detailed explanation
        analogy: Analogical explanation
        example: Concrete example
        exercise: Practice exercise/question

    """

    title: str = Field(..., description="Lesson title")
    concept: str = Field(..., description="Main concept being taught")
    explanation: str = Field(..., description="Detailed explanation")
    analogy: str | None = Field(None, description="Analogical explanation")
    example: str | None = Field(None, description="Concrete example")
    exercise: str | None = Field(None, description="Practice exercise/question")


class Section(BaseModel):
    """Section in syllabus.

    Attributes:
        title: Section title
        description: Section description
        lessons: List of lessons in this section

    """

    title: str = Field(..., description="Section title")
    description: str = Field(..., description="Section description")
    lessons: list[Lesson] = Field(..., description="List of lessons")


class Syllabus(BaseModel):
    """Syllabus structure for tutoring session.

    Attributes:
        title: Syllabus title
        description: Overall description
        sections: List of sections (2-4 sections, 2-3 lessons each)

    """

    title: str = Field(..., description="Syllabus title")
    description: str = Field(..., description="Overall description")
    sections: list[Section] = Field(..., description="List of sections (2-4 sections)")
