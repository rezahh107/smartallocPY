"""Validation helpers for business rules."""

from __future__ import annotations

from typing import Iterable, List

from ..models.student import Student
from ..models.mentor import Mentor


class ValidationService:
    """Wraps common validation logic for allocation inputs."""

    @staticmethod
    def validate_students(students: Iterable[dict]) -> List[Student]:
        """Validate and convert dictionaries to ``Student`` objects."""

        return [Student(**payload) for payload in students]

    @staticmethod
    def validate_mentors(mentors: Iterable[dict]) -> List[Mentor]:
        return [Mentor(**payload) for payload in mentors]
