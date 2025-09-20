from datetime import datetime

from src.core.models.assignment import Assignment, AssignmentStatus
from src.core.models.mentor import Mentor
from src.core.models.student import Student


def test_student_full_name():
    student = Student(id="s1", first_name="Ali", last_name="Rezaei")
    assert student.full_name == "Ali Rezaei"


def test_mentor_has_capacity():
    mentor = Mentor(id="m1", first_name="Sara", last_name="Karimi", capacity=3)
    assert mentor.has_capacity(current_load=2) is True
    assert mentor.has_capacity(current_load=3) is False


def test_assignment_defaults():
    assignment = Assignment(id="a1", student_id="s1", mentor_id="m1")
    assert assignment.status == AssignmentStatus.PENDING
    assert isinstance(assignment.created_at, datetime)
