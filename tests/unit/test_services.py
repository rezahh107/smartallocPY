from src.core.models.mentor import Mentor, MentorType
from src.core.models.student import Student
from src.core.services.allocation_service import AllocationService
from src.core.services.counter_service import CounterService


def _student_payload(**overrides):
    payload = {
        "national_id": "0013542419",
        "first_name": "علی",
        "last_name": "رضایی",
        "gender": 1,
        "edu_status": 1,
        "reg_center": 1,
        "reg_status": 0,
        "group_code": 105,
        "mobile": "09121234567",
    }
    payload.update(overrides)
    return payload


def test_allocation_service_assigns_students():
    students = [
        Student(**_student_payload(school_code=12345)),
        Student(
            **_student_payload(
                national_id="0024587966",
                first_name="ندا",
                last_name="مرادی",
                gender=0,
                reg_center=2,
                reg_status=1,
                mobile="00989121234567",
                group_code=205,
                school_code=None,
            )
        ),
    ]
    mentors = [
        Mentor(
            mentor_id=2002,
            first_name="حمید",
            last_name="احمدی",
            gender=1,
            mentor_type=MentorType.SCHOOL,
            allowed_groups=[105],
            special_schools=[12345],
            max_students=1,
        ),
        Mentor(
            mentor_id=2003,
            first_name="سارا",
            last_name="کریمی",
            gender=0,
            mentor_type=MentorType.NORMAL,
            allowed_groups=[205],
            max_students=1,
        ),
    ]

    service = AllocationService(counter_service=CounterService(prefix="T-"), default_capacity=1)
    assignments = service.allocate(students, mentors)

    assert len(assignments) == 2
    assert {assignment.mentor_id for assignment in assignments} == {"2002", "2003"}
    assert all(assignment.assignment_id.startswith("T-") for assignment in assignments)
