from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.models.student import Student


@pytest.fixture(autouse=True)
def reset_special_schools() -> None:
    """Ensure SPECIAL_SCHOOLS is reset between tests."""

    original = Student.SPECIAL_SCHOOLS
    Student.SPECIAL_SCHOOLS = frozenset()
    try:
        yield
    finally:
        Student.SPECIAL_SCHOOLS = original


def _base_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "national_id": "0012345679",
        "gender": 1,
        "edu_status": 1,
        "reg_center": 0,
        "reg_status": 0,
        "group_code": 3,
        "school_code": None,
        "mobile": "09123456789",
        "counter": "543571234",
    }
    payload.update(overrides)
    return payload


def test_special_school_student_type() -> None:
    Student.SPECIAL_SCHOOLS = frozenset({283})
    student = Student(**_base_payload(school_code=283))

    assert student.student_type == 1
    assert student.is_assignable() is True


def test_school_code_zero_values_normalize_to_none() -> None:
    Student.SPECIAL_SCHOOLS = frozenset({283})
    student = Student(**_base_payload(school_code="0"))

    assert student.school_code is None
    assert student.student_type == 0


def test_school_code_empty_string_normalizes_to_none() -> None:
    Student.SPECIAL_SCHOOLS = frozenset({283})
    student = Student(**_base_payload(school_code=""))

    assert student.school_code is None
    assert student.student_type == 0


def test_mobile_normalization_and_counter_validation() -> None:
    Student.SPECIAL_SCHOOLS = frozenset()
    student = Student(
        **_base_payload(
            national_id="1000000001",
            reg_center=2,
            reg_status=3,
            group_code=4,
            school_code=None,
            mobile="+98۹۱۲۳۴۵۶۷۸۹",
        )
    )

    assert student.mobile == "09123456789"
    assert student.counter == "543571234"
    assert student.is_assignable() is True


def test_invalid_counter_raises_validation_error() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Student(**_base_payload(counter="543361234"))

    assert "شمارنده باید مطابق الگوی" in str(exc_info.value)


def test_mobile_normalization_accepts_double_zero_prefix() -> None:
    student = Student(**_base_payload(mobile="00989121234567"))

    assert student.mobile == "09121234567"


def test_mobile_normalization_with_persian_digits() -> None:
    student = Student(**_base_payload(mobile="0098۹۱۲۳۴۵۶۷۸۹"))

    assert student.mobile == "09123456789"


def test_national_id_checksum_validation() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Student(**_base_payload(national_id="1111111111"))

    assert "کد ملی نامعتبر است" in str(exc_info.value)


def test_serialization_uses_aliases_and_excludes_none() -> None:
    Student.SPECIAL_SCHOOLS = frozenset({283})
    student = Student(**_base_payload(school_code=None, reg_status=3))

    data = student.to_dict()

    assert "student_type" not in data
    assert "مدرسه نهایی" not in data
    assert "کد مدرسه" not in data
    assert data["کدملی"] == "0012345679"
    assert data["جنسیت"] == 1


def test_school_code_persian_alias_enables_special_student_type() -> None:
    Student.SPECIAL_SCHOOLS = frozenset({283})
    student = Student(
        **{
            "کد مدرسه": 283,
            "کدملی": "0012345679",
            "جنسیت": 1,
            "وضعیت تحصیلی": 1,
            "مرکز ثبت نام": 0,
            "وضعیت ثبت نام": 0,
            "گروه آزمایشی نهایی": 3,
            "تلفن همراه داوطلب": "09123456789",
        }
    )

    assert student.school_code == 283
    assert student.student_type == 1
    data = student.to_dict()
    assert data["کد مدرسه"] == 283
    assert "مدرسه نهایی" not in data


def test_school_code_persian_alias_handles_empty_string() -> None:
    Student.SPECIAL_SCHOOLS = frozenset({283})
    student = Student(
        **{
            "کد مدرسه": "",
            "کدملی": "0012345679",
            "جنسیت": 0,
            "وضعیت تحصیلی": 0,
            "مرکز ثبت نام": 1,
            "وضعیت ثبت نام": 1,
            "گروه آزمایشی نهایی": 2,
            "تلفن همراه داوطلب": "09123456789",
        }
    )

    assert student.school_code is None
    assert student.student_type == 0
    data = student.to_dict()
    assert "کد مدرسه" not in data
    assert "مدرسه نهایی" not in data
