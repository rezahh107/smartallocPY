from src.core.models.assignment import Assignment, AssignmentStatus
from src.core.models.mentor import Mentor, MentorType
from src.core.models.student import Student


def _student_payload(**overrides):
    payload = {
        "national_id": "0013542419",
        "gender": 1,
        "edu_status": 1,
        "reg_center": 1,
        "reg_status": 0,
        "group_code": 105,
        "school_code": None,
        "mobile": "00989121234567",
        "counter": "543571234",
    }
    payload.update(overrides)
    return payload


def test_student_normalization_and_computed_type():
    Student.SPECIAL_SCHOOLS = frozenset({12345})
    student = Student(**_student_payload(school_code="12345"))

    assert student.mobile == "09121234567"
    assert student.counter == "543571234"
    assert student.student_type == 1
    assert student.is_assignable() is True


def test_student_handles_zero_school_codes():
    Student.SPECIAL_SCHOOLS = frozenset({12345})
    student = Student(**_student_payload(school_code="0"))

    assert student.school_code is None
    assert student.student_type == 0


def test_student_handles_empty_school_code_string():
    Student.SPECIAL_SCHOOLS = frozenset({98765})
    student = Student(**_student_payload(school_code=""))

    assert student.school_code is None
    assert student.student_type == 0


def test_student_rejects_invalid_national_id():
    Student.SPECIAL_SCHOOLS = frozenset()
    payload = _student_payload(national_id="1111111111")
    from pytest import raises

    with raises(ValueError) as exc_info:
        Student(**payload)
    assert "کد ملی نامعتبر است" in str(exc_info.value)


def test_student_is_assignable_respects_hakmat_code():
    Student.SPECIAL_SCHOOLS = frozenset()
    student = Student(**_student_payload(reg_status=3))
    assert student.is_assignable() is True


def test_student_mobile_accepts_double_zero_prefix():
    Student.SPECIAL_SCHOOLS = frozenset()
    student = Student(**_student_payload(mobile="00989129876543"))

    assert student.mobile == "09129876543"


def test_mentor_capacity_and_acceptance():
    Student.SPECIAL_SCHOOLS = frozenset({999})
    student = Student(**_student_payload(gender=0, group_code=205, reg_status=1, school_code=999))

    mentor = Mentor(
        mentor_id=3001,
        first_name="سارا",
        last_name="کریمی",
        gender=0,
        mentor_type=MentorType.SCHOOL,
        allowed_groups=[205],
        max_students=3,
        current_assignments=2,
        special_schools=[999],
    )

    assert mentor.capacity_remaining == 1
    assert mentor.can_accept_student(student) is True

    mentor.current_load = mentor.capacity
    assert mentor.can_accept_student(student) is False


def test_assignment_defaults():
    assignment = Assignment(id="a1", student_id="s1", mentor_id="m1")
    assert assignment.status == AssignmentStatus.PENDING
    assert assignment.assignment_id == "a1"
