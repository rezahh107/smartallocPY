from datetime import datetime

from src.core.models.assignment import Assignment, AssignmentStatus
from src.core.models.mentor import Mentor
from src.core.models.student import Student


def _student_payload(**overrides):
    payload = {
        "national_id": "0013542419",
        "first_name": "علی   احمد",
        "last_name": "رضایی",
        "gender": 1,
        "edu_status": 1,
        "reg_center": 1,
        "reg_status": 0,
        "group_code": 105,
        "mobile": "+989121234567",
    }
    payload.update(overrides)
    return payload


def test_student_full_name():
    student = Student(**_student_payload())
    assert student.first_name == "علی احمد"
    assert student.mobile == "09121234567"
    assert student.display_name == "رضایی، علی احمد"
    assert student.full_name == "علی احمد رضایی".replace("  ", " ").strip()
    assert student.student_type == 0
    assert "display_name" not in student.to_dict()


def test_student_is_assignable_respects_registration_status():
    student = Student(**_student_payload(reg_status=3))
    assert student.is_assignable() is False


def test_mentor_has_capacity():
    mentor = Mentor(id="m1", first_name="Sara", last_name="Karimi", capacity=3)
    assert mentor.has_capacity(current_load=2) is True
    assert mentor.has_capacity(current_load=3) is False


def test_assignment_defaults():
    assignment = Assignment(id="a1", student_id="s1", mentor_id="m1")
    assert assignment.status == AssignmentStatus.PENDING
    assert isinstance(assignment.created_at, datetime)
