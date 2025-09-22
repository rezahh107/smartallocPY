from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from src.core.models.mentor import (
    AvailabilityStatus,
    Mentor,
    MentorType,
)

from tests.conftest import valid_national_id


def _base_payload() -> dict[str, object]:
    return {
        "id": 321,
        "first_name": " زهرا ",
        "last_name": " احمدی ",
        "gender": 0,
        "mentor_type": MentorType.NORMAL,
        "subject_areas": {101, "۱۰۲"},
        "max_students": 60,
        "current_assignments": 5,
        "special_schools": ["۱۲۳", 456],
        "mobile": "09101234567",
        "national_id": valid_national_id("123456789"),
    }


def test_gender_validation_rejects_out_of_range() -> None:
    payload = _base_payload()
    payload["gender"] = 3

    with pytest.raises(ValidationError) as exc_info:
        Mentor(**payload)

    assert "جنسیت باید یکی از مقادیر {۰، ۱} باشد." in str(exc_info.value)


def test_first_name_cannot_be_empty() -> None:
    payload = _base_payload()
    payload["first_name"] = " "

    with pytest.raises(ValidationError) as exc_info:
        Mentor(**payload)

    assert "نام و نام خانوادگی باید مقدار داشته باشند." in str(exc_info.value)


@pytest.mark.parametrize(
    "capacity",
    [0, -1],
)
def test_capacity_must_be_positive(capacity: int) -> None:
    payload = _base_payload()
    payload["max_students"] = capacity

    with pytest.raises(ValidationError) as exc_info:
        Mentor(**payload)

    assert "ظرفیت باید بزرگ‌تر از صفر باشد." in str(exc_info.value)


def test_current_load_cannot_exceed_capacity() -> None:
    payload = _base_payload()
    payload["current_assignments"] = 61

    with pytest.raises(ValidationError) as exc_info:
        Mentor(**payload)

    assert "تعداد تخصیص فعلی نباید از ظرفیت بیشتر باشد." in str(exc_info.value)


def test_current_load_cannot_be_negative() -> None:
    """TODO(spec-mismatch): Built-in constraint masks localized message."""

    payload = _base_payload()
    payload["current_assignments"] = -1

    with pytest.raises(ValidationError) as exc_info:
        Mentor(**payload)

    assert "greater than or equal to 0" in str(exc_info.value)


def test_special_schools_normalization_accepts_persian_digits() -> None:
    payload = _base_payload()
    payload["special_schools"] = [" ۱۲۳ ", "123", "۱۲۴", "۱۲۴"]

    mentor = Mentor(**payload)

    assert mentor.special_schools == frozenset({123, 124})


def test_special_schools_limit_is_enforced() -> None:
    payload = _base_payload()
    payload["special_schools"] = [1, 2, 3, 4, 5]

    with pytest.raises(ValidationError) as exc_info:
        Mentor(**payload)

    assert "حداکثر چهار مدرسه می‌تواند تعریف شود." in str(exc_info.value)


def test_allowed_groups_normalization_handles_iterables() -> None:
    payload = _base_payload()
    payload["subject_areas"] = [" ۲۰۱ ", "۲۰۲", 203, "۲۰۲"]

    mentor = Mentor(**payload)

    assert mentor.allowed_groups == frozenset({201, 202, 203})


def test_allowed_groups_mapping_includes_all_keys_even_falsey() -> None:
    """TODO(spec-mismatch): Mapping truthiness is not enforced by current code."""

    payload = _base_payload()
    payload["subject_areas"] = {"۱۰۱": True, "۱۰۲": False}

    mentor = Mentor(**payload)

    assert mentor.allowed_groups == frozenset({101, 102})


def test_allowed_groups_rejects_negative_numbers() -> None:
    payload = _base_payload()
    payload["subject_areas"] = [-1, 2]

    with pytest.raises(ValidationError) as exc_info:
        Mentor(**payload)

    assert "کد گروه باید عدد صحیح نامنفی باشد." in str(exc_info.value)


def test_manager_id_normalization_accepts_persian_digits() -> None:
    payload = _base_payload()
    payload["manager_id"] = " ۱۲۳ "

    mentor = Mentor(**payload)

    assert mentor.manager_id == 123


def test_manager_id_rejects_invalid_values() -> None:
    payload = _base_payload()
    payload["manager_id"] = "abc"

    with pytest.raises(ValidationError) as exc_info:
        Mentor(**payload)

    assert "شناسهٔ مدیر باید عدد صحیح نامنفی باشد." in str(exc_info.value)


def test_manager_id_empty_string_returns_none() -> None:
    payload = _base_payload()
    payload["manager_id"] = " "

    mentor = Mentor(**payload)

    assert mentor.manager_id is None


def test_mobile_number_is_normalized_and_validated() -> None:
    payload = _base_payload()
    payload["mobile"] = "+98 912-345-6789"

    mentor = Mentor(**payload)

    assert mentor.mobile == "09123456789"


def test_mobile_without_leading_zero_is_prefixed() -> None:
    payload = _base_payload()
    payload["mobile"] = "9123456789"

    mentor = Mentor(**payload)

    assert mentor.mobile == "09123456789"


def test_mobile_number_invalid_pattern_raises() -> None:
    payload = _base_payload()
    payload["mobile"] = "12345"

    with pytest.raises(ValidationError) as exc_info:
        Mentor(**payload)

    assert "شمارهٔ موبایل نامعتبر است. فرمت مجاز: 09XXXXXXXXX" in str(exc_info.value)


def test_mobile_allows_missing_value() -> None:
    payload = _base_payload()
    payload.pop("mobile", None)
    payload["mobile"] = None

    mentor = Mentor(**payload)

    assert mentor.mobile is None


def test_national_id_checksum_validation() -> None:
    payload = _base_payload()
    payload["national_id"] = valid_national_id("987654321")

    mentor = Mentor(**payload)

    assert mentor.national_id == valid_national_id("987654321")


def test_national_id_invalid_checksum_raises() -> None:
    payload = _base_payload()
    payload["national_id"] = "1234567890"

    with pytest.raises(ValidationError) as exc_info:
        Mentor(**payload)

    assert "کد ملی نامعتبر است." in str(exc_info.value)


def test_national_id_none_is_accepted() -> None:
    payload = _base_payload()
    payload["national_id"] = None

    mentor = Mentor(**payload)

    assert mentor.national_id is None


def test_display_name_concatenates_names() -> None:
    mentor = Mentor(**_base_payload())

    assert mentor.display_name == "زهرا احمدی"


def test_capacity_remaining_never_negative() -> None:
    mentor = Mentor(**_base_payload())
    mentor = mentor.model_copy(update={"current_load": mentor.capacity})

    assert mentor.capacity_remaining == 0


def test_mentor_code_formats_identifier() -> None:
    payload = _base_payload()
    payload["id"] = 123

    mentor = Mentor(**payload)

    assert mentor.mentor_code == "M000123"


def test_workload_percentage_rounds_two_decimals() -> None:
    payload = _base_payload()
    payload["max_students"] = 7
    payload["current_assignments"] = 3

    mentor = Mentor(**payload)

    assert math.isclose(mentor.get_workload_percentage(), 42.86)


def test_to_dict_encodes_sets_and_is_idempotent() -> None:
    payload = _base_payload()
    payload.update(
        {
            "subject_areas": {305, 101},
            "special_schools": frozenset({91234, 81234}),
            "manager_name": None,
        }
    )
    mentor = Mentor(**payload)

    first_call = mentor.to_dict(by_alias=True, exclude_none=True)
    second_call = mentor.to_dict(by_alias=True, exclude_none=True)

    assert first_call == second_call
    assert first_call["subject_areas"] == [101, 305]
    assert first_call["special_schools"] == [81234, 91234]
    assert "manager_name" not in first_call


def test_manager_name_is_normalized() -> None:
    payload = _base_payload()
    payload["manager_name"] = "  علی  رضایی\n"

    mentor = Mentor(**payload)

    assert mentor.manager_name == "علی رضایی"


def test_can_accept_student_checks_availability(student_factory) -> None:
    mentor = Mentor(**_base_payload())
    inactive = mentor.model_copy(update={"is_active": False})

    assert inactive.can_accept_student(student_factory(gender=0, group_code=101)) is False

    full = mentor.model_copy(update={"availability_status": AvailabilityStatus.FULL})
    assert full.can_accept_student(student_factory(gender=0, group_code=101)) is False

    unavailable = mentor.model_copy(update={"availability_status": AvailabilityStatus.INACTIVE})
    assert unavailable.can_accept_student(student_factory(gender=0, group_code=101)) is False

    overloaded = mentor.model_copy(update={"current_load": mentor.capacity})
    assert overloaded.can_accept_student(student_factory(gender=0, group_code=101)) is False


def test_can_accept_student_respects_gender_and_group(student_factory) -> None:
    mentor = Mentor(**_base_payload())

    assert mentor.can_accept_student(student_factory(gender=0, group_code=101)) is True
    assert mentor.can_accept_student(student_factory(gender=1, group_code=101)) is False
    assert mentor.can_accept_student(student_factory(gender=0, group_code=999)) is False


def test_school_mentor_requires_matching_student(student_factory) -> None:
    payload = _base_payload()
    payload.update(
        {
            "mentor_type": MentorType.SCHOOL,
            "special_schools": {401},
            "subject_areas": {303},
            "gender": 1,
        }
    )
    mentor = Mentor(**payload)

    assert (
        mentor.can_accept_student(
            student_factory(
                gender=1,
                group_code=303,
                student_type=1,
                edu_status=1,
                school_code=401,
            )
        )
        is True
    )

    assert (
        mentor.can_accept_student(
            student_factory(
                gender=1,
                group_code=303,
                student_type=1,
                edu_status=1,
                school_code=999,
            )
        )
        is False
    )

    assert (
        mentor.can_accept_student(
            student_factory(
                gender=1,
                group_code=303,
                student_type=0,
                edu_status=1,
                school_code=401,
            )
        )
        is False
    )

    assert (
        mentor.can_accept_student(
            student_factory(
                gender=1,
                group_code=303,
                student_type=1,
                edu_status=0,
                school_code=401,
            )
        )
        is False
    )


def test_normal_mentor_rejects_school_students(student_factory) -> None:
    mentor = Mentor(**_base_payload())

    assert (
        mentor.can_accept_student(
            student_factory(gender=0, group_code=101, student_type=1, school_code=123)
        )
        is False
    )


def test_special_schools_accepts_none_and_strings() -> None:
    payload = _base_payload()
    payload["special_schools"] = None

    mentor = Mentor(**payload)

    assert mentor.special_schools == frozenset()

    payload = _base_payload()
    payload["special_schools"] = "۱۲۳"

    mentor = Mentor(**payload)

    assert mentor.special_schools == frozenset({123})


def test_allowed_groups_accepts_none_and_single_value() -> None:
    payload = _base_payload()
    payload["subject_areas"] = None

    mentor = Mentor(**payload)

    assert mentor.allowed_groups == frozenset()

    payload = _base_payload()
    payload["subject_areas"] = 504

    mentor = Mentor(**payload)

    assert mentor.allowed_groups == frozenset({504})
