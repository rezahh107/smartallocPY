from src.core.models.mentor import Mentor
from src.core.models.student import Student
from src.core.services.allocation_service import AllocationService


def test_allocation_flow_prefers_preferences():
    students = [
        Student(
            national_id="0013542419",
            first_name="علی",
            last_name="رضایی",
            gender=1,
            edu_status=1,
            reg_center=1,
            reg_status=1,
            group_code=105,
            mobile="09121234567",
        ),
        Student(
            national_id="0024587966",
            first_name="ندا",
            last_name="مرادی",
            gender=0,
            edu_status=1,
            reg_center=0,
            reg_status=3,
            group_code=205,
            mobile="09151234567",
        ),
    ]
    mentors = [
        Mentor(id="m1", first_name="Sara", last_name="Karimi", capacity=1),
        Mentor(id="m2", first_name="Hamid", last_name="Ahmadi", capacity=2),
    ]

    service = AllocationService()
    assignments = service.allocate(students, mentors)

    assert len(assignments) == 1
    assignment = assignments[0]
    assert assignment.student_id == "0013542419"
    assert assignment.mentor_id in {"m1", "m2"}
