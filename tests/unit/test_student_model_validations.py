from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.models.student import Student

from tests.conftest import valid_national_id


def test_student_accepts_persian_aliases_and_serializes(monkeypatch) -> None:
    monkeypatch.setattr(Student, "SPECIAL_SCHOOLS", frozenset({401}))
    student = Student.model_validate(
        {
            "کدملی": valid_national_id("111222333"),
            "جنسیت": "۱",
            "وضعیت تحصیلی": "۱",
            "مرکز ثبت نام": "۱",
            "وضعیت ثبت نام": "۳",
            "گروه آزمایشی نهایی": "201",
            "کد مدرسه": "۴۰۱",
            "شماره موبایل": "+98 912 345 6789",
            "شمارنده": "۱۴۳۷۳۰۰۰۱",
        }
    )

    assert student.gender == 1
    assert student.mobile == "09123456789"
    assert student.school_code == 401
    assert student.student_type == 1

    data = student.to_dict()
    assert data["کدملی"] == student.national_id
    assert data["تلفن همراه داوطلب"] == "09123456789"
    assert "student_type" not in data
    assert "شمارنده" in data


def test_student_gender_validation_message() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Student(
            national_id=valid_national_id("321654987"),
            gender=3,
            edu_status=1,
            reg_center=1,
            reg_status=1,
            group_code=101,
            school_code=None,
            mobile="09123456789",
        )

    assert "جنسیت باید یکی از مقادیر ۰ یا ۱ باشد" in str(exc_info.value)


def test_student_mobile_validation_enforces_pattern() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Student(
            national_id=valid_national_id("321654987"),
            gender=1,
            edu_status=1,
            reg_center=1,
            reg_status=1,
            group_code=101,
            school_code=None,
            mobile="123",
        )

    assert "شماره موبایل باید با 09 شروع شده و ۱۱ رقم باشد" in str(exc_info.value)


def test_student_counter_pattern_validation() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Student(
            national_id=valid_national_id("654321987"),
            gender=1,
            edu_status=1,
            reg_center=1,
            reg_status=1,
            group_code=101,
            school_code=None,
            mobile="09123456789",
            counter="۱۴۰۱۲۳",
        )

    assert "شمارنده باید مطابق الگوی YY357#### یا YY373#### باشد" in str(exc_info.value)


def test_school_code_zero_is_normalized_to_none() -> None:
    student = Student(
        national_id=valid_national_id("852741963"),
        gender=0,
        edu_status=1,
        reg_center=1,
        reg_status=1,
        group_code=101,
        school_code="0",
        mobile="09123456789",
    )

    assert student.school_code is None
