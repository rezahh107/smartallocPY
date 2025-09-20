from src.core.models.mentor import Mentor
from src.core.models.student import Student
from src.core.services.allocation_service import AllocationService


def test_allocation_flow_prefers_preferences():
    students = [
        Student(id="s1", first_name="Ali", last_name="Rezaei", preferences=["m2"]),
        Student(id="s2", first_name="Neda", last_name="Moradi"),
    ]
    mentors = [
        Mentor(id="m1", first_name="Sara", last_name="Karimi", capacity=1),
        Mentor(id="m2", first_name="Hamid", last_name="Ahmadi", capacity=2),
    ]

    service = AllocationService()
    assignments = service.allocate(students, mentors)

    preference_assignment = next(item for item in assignments if item.student_id == "s1")
    assert preference_assignment.mentor_id == "m2"
