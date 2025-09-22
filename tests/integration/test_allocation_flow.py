from __future__ import annotations

from src.core.models.mentor import Mentor, MentorType
from src.core.models.student import Student
from src.core.services.allocation_service import AllocationService
from src.core.services.counter_service import CounterService

from tests.conftest import valid_national_id


def _make_student(
    prefix: str,
    *,
    gender: int,
    group_code: int,
    edu_status: int = 1,
    reg_status: int = 1,
    school_code: int | None = None,
) -> Student:
    return Student(
        national_id=valid_national_id(prefix),
        gender=gender,
        edu_status=edu_status,
        reg_center=1,
        reg_status=reg_status,
        group_code=group_code,
        school_code=school_code,
        mobile="09123456789",
    )


def test_allocation_service_assigns_students_respecting_constraints(monkeypatch) -> None:
    monkeypatch.setattr(Student, "SPECIAL_SCHOOLS", frozenset({401}))
    mentors = [
        Mentor(
            mentor_id=1,
            first_name="نرگس",
            last_name="احمدی",
            gender=0,
            mentor_type=MentorType.NORMAL,
            allowed_groups={201},
        ),
        Mentor(
            mentor_id=2,
            first_name="مهدی",
            last_name="کاظمی",
            gender=1,
            mentor_type=MentorType.SCHOOL,
            special_schools={401},
            allowed_groups={303},
        ),
    ]
    students = [
        _make_student("123456780", gender=0, group_code=201),
        _make_student("234567891", gender=1, group_code=303, school_code=401),
        _make_student("345678912", gender=0, group_code=999),
    ]

    service = AllocationService(counter_service=CounterService(prefix="A-"))

    assignments = service.allocate(students, mentors)

    assert len(assignments) == 2
    mapping = {assignment.student_id: assignment.mentor_id for assignment in assignments}
    assert mapping[students[0].national_id] == str(mentors[0].mentor_id)
    assert mapping[students[1].national_id] == str(mentors[1].mentor_id)
    assert students[2].national_id not in mapping

    assert mentors[0].current_load == 1
    assert mentors[1].current_load == 1
