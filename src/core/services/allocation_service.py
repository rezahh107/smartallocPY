"""Core allocation engine for matching students to mentors."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from ..models.assignment import Assignment, AssignmentStatus
from ..models.mentor import Mentor
from ..models.student import Student
from ..utils.mobile_normalizer import normalize_mobile_number
from ...config.settings import get_settings
from .counter_service import CounterService


class AllocationError(Exception):
    """Raised when allocation cannot proceed."""


class AllocationService:
    """Allocate students to mentors based on capacity and preferences."""

    def __init__(
        self,
        counter_service: Optional[CounterService] = None,
        default_capacity: Optional[int] = None,
    ) -> None:
        settings = get_settings()
        self.counter = counter_service or CounterService(prefix="A-")
        self.default_capacity = default_capacity or settings.default_mentor_capacity

    def allocate(self, students: Iterable[Student], mentors: Iterable[Mentor]) -> List[Assignment]:
        """Allocate students to mentors respecting capacities."""

        active_students = [student for student in students if student.is_assignable()]
        active_mentors = [mentor for mentor in mentors if mentor.active]
        if not active_mentors:
            raise AllocationError("No active mentors available for allocation")

        mentor_lookup: Dict[str, Mentor] = {mentor.mentor_id: mentor for mentor in active_mentors}
        remaining_capacity = {
            mentor_id: mentor.capacity if mentor.capacity > 0 else self.default_capacity
            for mentor_id, mentor in mentor_lookup.items()
        }
        allocations: List[Assignment] = []

        for student in active_students:
            if student.mobile_number:
                student.mobile_number = normalize_mobile_number(student.mobile_number)
            mentor_id = self._select_mentor(student, remaining_capacity, mentor_lookup)
            if mentor_id is None:
                continue
            remaining_capacity[mentor_id] -= 1
            allocations.append(
                Assignment(
                    assignment_id=self.counter.next(),
                    student_id=student.student_id,
                    mentor_id=mentor_id,
                    status=AssignmentStatus.CONFIRMED,
                )
            )
        return allocations

    def _select_mentor(
        self,
        student: Student,
        remaining_capacity: Dict[str, int],
        mentors: Dict[str, Mentor],
    ) -> Optional[str]:
        """Select the most suitable mentor for the student."""

        for preference in student.preferences:
            if remaining_capacity.get(preference, 0) > 0:
                return preference

        available = [
            (capacity, mentor_id)
            for mentor_id, capacity in remaining_capacity.items()
            if capacity > 0 and mentors[mentor_id].active
        ]
        if not available:
            return None

        available.sort(key=lambda item: (-item[0], mentors[item[1]].full_name))
        _, mentor_id = available[0]
        return mentor_id
