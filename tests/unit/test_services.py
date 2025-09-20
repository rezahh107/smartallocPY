from src.core.models.mentor import Mentor
from src.core.models.mentor import Mentor
from src.core.models.mentor import Mentor
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
                school_code=None,
            )
        ),
    ]
    mentors = [
        Mentor(id="m1", first_name="Sara", last_name="Karimi", capacity=1),
        Mentor(id="m2", first_name="Hamid", last_name="Ahmadi", capacity=1),
    ]

    service = AllocationService(counter_service=CounterService(prefix="T-"), default_capacity=1)
    assignments = service.allocate(students, mentors)

    assert len(assignments) == 2
    assert {assignment.mentor_id for assignment in assignments} == {"m1", "m2"}
    assert all(assignment.assignment_id.startswith("T-") for assignment in assignments)
