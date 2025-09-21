from src.core.models.mentor import Mentor, MentorType
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
        Mentor(
            mentor_id=1001,
            first_name="سارا",
            last_name="کریمی",
            gender=0,
            mentor_type=MentorType.NORMAL,
            allowed_groups=[205],
            max_students=1,
        ),
        Mentor(
            mentor_id=1002,
            first_name="حمید",
            last_name="احمدی",
            gender=1,
            mentor_type=MentorType.NORMAL,
            allowed_groups=[105],
            max_students=2,
        ),
    ]

    service = AllocationService()
    assignments = service.allocate(students, mentors)

    assert len(assignments) == 1
    assignment = assignments[0]
    assert assignment.student_id == "0013542419"
    assert assignment.mentor_id in {"1001", "1002"}
