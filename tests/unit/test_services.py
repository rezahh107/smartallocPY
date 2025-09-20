from src.core.models.mentor import Mentor
from src.core.models.student import Student
from src.core.services.allocation_service import AllocationService
from src.core.services.counter_service import CounterService


def test_allocation_service_assigns_students():
    students = [
        Student(id="s1", first_name="Ali", last_name="Rezaei"),
        Student(id="s2", first_name="Neda", last_name="Moradi"),
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
