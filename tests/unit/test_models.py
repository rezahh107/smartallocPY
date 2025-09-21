from datetime import datetime

from src.core.models.assignment import Assignment, AssignmentStatus
from src.core.models.mentor import Mentor, MentorType
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


def test_mentor_capacity_and_acceptance():
    mentor = Mentor(
        mentor_id=3001,
        first_name="سارا",
        last_name="کریمی",
        gender=0,
        mentor_type=MentorType.NORMAL,
        allowed_groups=[105],
        max_students=3,
        current_assignments=2,
    )
    student = Student(**_student_payload(gender=0))

    assert mentor.capacity_remaining == 1
    assert mentor.can_accept_student(student) is True

    mentor.current_load = mentor.capacity
    assert mentor.can_accept_student(student) is False


def test_assignment_defaults():
    assignment = Assignment(id="a1", student_id="s1", mentor_id="m1")
    assert assignment.status == AssignmentStatus.PENDING
    assert isinstance(assignment.created_at, datetime)
