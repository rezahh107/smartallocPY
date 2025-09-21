"""Unit tests for the Mentor model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.models.mentor import AvailabilityStatus, Mentor, MentorType


class _StudentStub:
    """Simple student-like object for mentor checks."""

    def __init__(
        self,
        *,
        gender: int = 1,
        edu_status: int = 1,
        student_type: int = 0,
        group_code: int = 101,
        school_code: int | None = None,
    ) -> None:
        self.gender = gender
        self.edu_status = edu_status
        self.student_type = student_type
        self.group_code = group_code
        self.school_code = school_code


def test_minimal_valid_mentor_creation() -> None:
    """Creating a mentor with minimal valid payload should succeed."""

    mentor = Mentor(
        mentor_id=12,
        first_name=" زهرا ",
        last_name=" احمدی",
        gender=0,
        mentor_type=MentorType.NORMAL,
        allowed_groups=[101, 102],
        current_assignments=10,
    )

    assert mentor.display_name == "زهرا احمدی"
    assert mentor.capacity == 60
    assert mentor.current_load == 10
    assert mentor.capacity_remaining == 50
    assert mentor.mentor_code == "M000012"


def test_alias_fields_and_normalization() -> None:
    """Aliases for legacy fields should populate canonical names."""

    mentor = Mentor(
        mentor_id=3,
        first_name="علی",
        last_name="کاظمی",
        gender=1,
        mentor_type="عادی",
        subject_areas=[201],
        max_students=80,
        current_assignments=5,
        mobile="۰۹۱۲۳۴۵۶۷۸۹",
    )

    assert mentor.allowed_groups == [201]
    assert mentor.capacity == 80
    assert mentor.mobile == "09123456789"


@pytest.mark.parametrize(
    "field, payload, message",
    [
        (
            "mobile",
            {"mobile": "123"},
            "شمارهٔ موبایل نامعتبر است",
        ),
        (
            "national_id",
            {"national_id": "1234567890"},
            "کد ملی نامعتبر است",
        ),
        (
            "special_schools",
            {"special_schools": [1, 2, 3, 4, 5]},
            "حداکثر چهار مدرسه",
        ),
    ],
)
def test_invalid_fields_raise_errors(field: str, payload: dict[str, object], message: str) -> None:
    """Invalid payloads should raise ValidationError with Persian messages."""

    with pytest.raises(ValidationError) as exc_info:
        Mentor(
            mentor_id=1,
            first_name="سارا",
            last_name="محمدی",
            gender=0,
            mentor_type=MentorType.NORMAL,
            allowed_groups=[101],
            **payload,
        )

    assert message in str(exc_info.value)


def test_current_load_cannot_exceed_capacity() -> None:
    """Current load larger than capacity should not be accepted."""

    with pytest.raises(ValidationError) as exc_info:
        Mentor(
            mentor_id=7,
            first_name="رضا",
            last_name="اکبری",
            gender=1,
            mentor_type=MentorType.NORMAL,
            allowed_groups=[101],
            max_students=5,
            current_assignments=6,
        )

    assert "تعداد تخصیص فعلی" in str(exc_info.value)


def test_school_student_requires_matching_school_mentor() -> None:
    """School type students must match school mentors and school codes."""

    mentor = Mentor(
        mentor_id=22,
        first_name="حمید",
        last_name="افشار",
        gender=1,
        mentor_type=MentorType.SCHOOL,
        allowed_groups=[101],
        special_schools=[91234],
    )

    accepted = mentor.can_accept_student(
        _StudentStub(student_type=1, school_code=91234, group_code=101)
    )
    rejected = mentor.can_accept_student(
        _StudentStub(student_type=1, school_code=91555, group_code=101)
    )

    assert accepted is True
    assert rejected is False


def test_graduate_rejected_by_school_mentor() -> None:
    """Graduated students should not be assigned to school mentors."""

    mentor = Mentor(
        mentor_id=9,
        first_name="جواد",
        last_name="فرهمند",
        gender=1,
        mentor_type=MentorType.SCHOOL,
        allowed_groups=[101],
        special_schools=[90001],
    )

    result = mentor.can_accept_student(
        _StudentStub(student_type=1, school_code=90001, edu_status=0)
    )

    assert result is False


def test_normal_student_not_sent_to_school_mentor() -> None:
    """Normal students should be rejected by school mentors."""

    mentor = Mentor(
        mentor_id=15,
        first_name="مینا",
        last_name="ستوده",
        gender=0,
        mentor_type=MentorType.SCHOOL,
        allowed_groups=[202],
        special_schools=[50001],
    )

    result = mentor.can_accept_student(
        _StudentStub(gender=0, student_type=0, group_code=202)
    )

    assert result is False


def test_availability_and_status_controls_acceptance() -> None:
    """Inactive mentors or full capacity must reject students."""

    mentor = Mentor(
        mentor_id=40,
        first_name="سحر",
        last_name="کریمی",
        gender=0,
        mentor_type=MentorType.NORMAL,
        allowed_groups=[110],
        current_assignments=60,
    )

    assert (
        mentor.can_accept_student(_StudentStub(gender=0, group_code=110)) is False
    )

    mentor_full = mentor.model_copy(update={"current_load": 30})
    mentor_full.availability_status = AvailabilityStatus.FULL
    assert (
        mentor_full.can_accept_student(_StudentStub(gender=0, group_code=110))
        is False
    )


def test_get_workload_percentage() -> None:
    """Workload percentage should be rounded to two decimal digits."""

    mentor = Mentor(
        mentor_id=5,
        first_name="پریا",
        last_name="معتمد",
        gender=0,
        mentor_type=MentorType.NORMAL,
        allowed_groups=[101],
        max_students=80,
        current_assignments=20,
    )

    assert mentor.get_workload_percentage() == 25.0
