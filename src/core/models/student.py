"""Pydantic model for representing student records in the allocation system."""

from __future__ import annotations

import re
from typing import Any, ClassVar, FrozenSet, Optional

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    computed_field,
    field_validator,
)

_DIGIT_TRANSLATION = str.maketrans(
    {
        "۰": "0",
        "۱": "1",
        "۲": "2",
        "۳": "3",
        "۴": "4",
        "۵": "5",
        "۶": "6",
        "۷": "7",
        "۸": "8",
        "۹": "9",
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
    }
)
_MOBILE_PATTERN = re.compile(r"^09\d{9}$")
_COUNTER_PATTERN = re.compile(r"^\d{2}(357|373)\d{4}$")
_ONLY_DIGITS_RE = re.compile(r"\D+")


class Student(BaseModel):
    """Validated representation of a student record for allocation workflows.

    Attributes:
        national_id: Ten-digit Iranian national identification number.
        gender: Student gender code (0: female, 1: male).
        edu_status: Educational status (0: graduate, 1: student).
        reg_center: Registration center code (0, 1, or 2).
        reg_status: Registration status code (0, 1, or 3). Hakmat uses code 3.
        group_code: Positive integer representing the exam group.
        school_code: Optional school code. Determines student type when present
            in ``SPECIAL_SCHOOLS``.
        mobile: Normalized mobile number in ``09123456789`` format.
        counter: Optional counter value following ``YY357####`` or ``YY373####``.
        student_type: Computed field derived from ``SPECIAL_SCHOOLS``.
    """

    SPECIAL_SCHOOLS: ClassVar[FrozenSet[int]] = frozenset()

    model_config = ConfigDict(
        validate_assignment=True,
        populate_by_name=True,
        extra="ignore",
    )

    national_id: str = Field(
        ...,
        description="کد ملی ۱۰ رقمی",
        validation_alias=AliasChoices(
            "national_id",
            "کدملی",
            "کد ملی",
            "کد‌ملی",
        ),
        serialization_alias="کدملی",
    )
    gender: int = Field(
        ...,
        description="جنسیت دانش‌آموز",
        validation_alias=AliasChoices("gender", "جنسیت"),
        serialization_alias="جنسیت",
    )
    edu_status: int = Field(
        ...,
        description="وضعیت تحصیلی",
        validation_alias=AliasChoices("edu_status", "وضعیت تحصیلی"),
        serialization_alias="وضعیت تحصیلی",
    )
    reg_center: int = Field(
        ...,
        description="مرکز ثبت‌نام",
        validation_alias=AliasChoices("reg_center", "مرکز ثبت نام", "مرکز ثبت‌نام"),
        serialization_alias="مرکز ثبت نام",
    )
    reg_status: int = Field(
        ...,
        description="وضعیت ثبت‌نام",
        validation_alias=AliasChoices("reg_status", "وضعیت ثبت نام", "وضعیت ثبت‌نام"),
        serialization_alias="وضعیت ثبت نام",
    )
    group_code: int = Field(
        ...,
        description="کد گروه",
        validation_alias=AliasChoices("group_code", "گروه آزمایشی نهایی"),
        serialization_alias="گروه آزمایشی نهایی",
    )
    school_code: Optional[int] = Field(
        default=None,
        description="کد مدرسه نهایی",
        validation_alias=AliasChoices("school_code", "مدرسه نهایی", "کد مدرسه"),
        serialization_alias="کد مدرسه",
    )
    mobile: str = Field(
        ...,
        description="شماره موبایل استاندارد",
        validation_alias=AliasChoices(
            "mobile",
            "mobile_phone",
            "mobile_number",
            "تلفن همراه داوطلب",
            "شماره موبایل",
            "شماره همراه",
        ),
        serialization_alias="تلفن همراه داوطلب",
    )
    counter: Optional[str] = Field(
        default=None,
        description="شمارنده اختیاری",
        validation_alias=AliasChoices("counter", "شمارنده"),
        serialization_alias="شمارنده",
    )

    @field_validator("national_id", mode="before")
    @classmethod
    def _normalize_national_id(cls, value: Any) -> str:
        """Normalize the national ID to a 10-digit ASCII string."""

        if value is None:
            raise ValueError("کد ملی الزامی است")
        text = str(value).strip().translate(_DIGIT_TRANSLATION)
        digits_only = _ONLY_DIGITS_RE.sub("", text)
        if len(digits_only) != 10:
            raise ValueError("کد ملی باید دقیقاً ۱۰ رقم باشد")
        return digits_only

    @field_validator("national_id")
    @classmethod
    def _validate_national_id(cls, value: str) -> str:
        """Validate the Iranian national ID checksum."""

        if value == value[0] * 10:
            raise ValueError("کد ملی نامعتبر است")
        digits = [int(char) for char in value]
        checksum = digits[-1]
        total = sum(digits[i] * (10 - i) for i in range(9))
        remainder = total % 11
        expected = remainder if remainder < 2 else 11 - remainder
        if checksum != expected:
            raise ValueError("کد ملی نامعتبر است")
        return value

    @field_validator("gender", mode="before")
    @classmethod
    def _normalize_gender(cls, value: Any) -> int:
        """Convert the gender value to integer before validation."""

        if value is None:
            raise ValueError("جنسیت باید مشخص شود")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValueError("جنسیت باید به صورت عددی وارد شود") from exc

    @field_validator("gender")
    @classmethod
    def _validate_gender(cls, value: int) -> int:
        """Ensure gender is either 0 or 1."""

        if value not in {0, 1}:
            raise ValueError("جنسیت باید یکی از مقادیر ۰ یا ۱ باشد")
        return value

    @field_validator("edu_status", mode="before")
    @classmethod
    def _normalize_edu_status(cls, value: Any) -> int:
        """Convert educational status to integer before validation."""

        if value is None:
            raise ValueError("وضعیت تحصیلی الزامی است")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValueError("وضعیت تحصیلی باید عددی باشد") from exc

    @field_validator("edu_status")
    @classmethod
    def _validate_edu_status(cls, value: int) -> int:
        """Ensure educational status is 0 or 1."""

        if value not in {0, 1}:
            raise ValueError("وضعیت تحصیلی باید یکی از مقادیر ۰ یا ۱ باشد")
        return value

    @field_validator("reg_center", mode="before")
    @classmethod
    def _normalize_reg_center(cls, value: Any) -> int:
        """Convert registration center to integer before validation."""

        if value is None:
            raise ValueError("مرکز ثبت نام الزامی است")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValueError("مرکز ثبت نام باید عددی باشد") from exc

    @field_validator("reg_center")
    @classmethod
    def _validate_reg_center(cls, value: int) -> int:
        """Ensure registration center is one of the allowed codes."""

        if value not in {0, 1, 2}:
            raise ValueError("مرکز ثبت نام باید یکی از {۰، ۱، ۲} باشد")
        return value

    @field_validator("reg_status", mode="before")
    @classmethod
    def _normalize_reg_status(cls, value: Any) -> int:
        """Convert registration status to integer before validation."""

        if value is None:
            raise ValueError("وضعیت ثبت نام الزامی است")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValueError("وضعیت ثبت نام باید عددی باشد") from exc

    @field_validator("reg_status")
    @classmethod
    def _validate_reg_status(cls, value: int) -> int:
        """Ensure registration status includes Hakmat code 3."""

        if value not in {0, 1, 3}:
            raise ValueError("وضعیت ثبت نام باید یکی از {۰، ۱، ۳} باشد")
        return value

    @field_validator("group_code", mode="before")
    @classmethod
    def _normalize_group_code(cls, value: Any) -> int:
        """Convert group code to integer before validation."""

        if value is None:
            raise ValueError("کد گروه الزامی است")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("کد گروه باید عددی باشد") from exc

    @field_validator("group_code")
    @classmethod
    def _validate_group_code(cls, value: int) -> int:
        """Ensure group code is a positive integer."""

        if value <= 0:
            raise ValueError("کد گروه باید عددی بزرگتر از صفر باشد")
        return value

    @field_validator("school_code", mode="before")
    @classmethod
    def _normalize_school_code(cls, value: Any) -> Optional[int]:
        """Normalize school code by handling sentinel values explicitly."""

        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            if stripped == "" or stripped == "0":
                return None
            value = stripped
        if value in {0, "0"}:
            return None
        try:
            code = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("کد مدرسه باید عددی باشد") from exc
        if code <= 0:
            raise ValueError("کد مدرسه باید عددی بزرگتر از صفر باشد")
        return code

    @field_validator("mobile", mode="before")
    @classmethod
    def _normalize_mobile(cls, value: Any) -> str:
        """Normalize the mobile number to the 09XXXXXXXXX format."""

        if value is None:
            raise ValueError("شماره موبایل باید با 09 شروع شده و ۱۱ رقم باشد")
        text = str(value).strip()
        if text == "":
            raise ValueError("شماره موبایل باید با 09 شروع شده و ۱۱ رقم باشد")
        text = text.translate(_DIGIT_TRANSLATION)
        text = re.sub(r"[\s\-()]+", "", text)
        if text.startswith("+"):
            text = text[1:]
        if text.startswith("00"):
            text = text[2:]
        if text.startswith("98"):
            text = text[2:]
        digits_only = _ONLY_DIGITS_RE.sub("", text)
        if len(digits_only) == 10 and digits_only.startswith("9"):
            digits_only = f"0{digits_only}"
        if not _MOBILE_PATTERN.fullmatch(digits_only):
            raise ValueError("شماره موبایل باید با 09 شروع شده و ۱۱ رقم باشد")
        return digits_only

    @field_validator("counter", mode="before")
    @classmethod
    def _normalize_counter(cls, value: Any) -> Optional[str]:
        """Normalize the optional counter to ASCII digits and validate pattern."""

        if value is None:
            return None
        text = str(value).strip()
        if text == "":
            return None
        text = text.translate(_DIGIT_TRANSLATION)
        digits_only = _ONLY_DIGITS_RE.sub("", text)
        if digits_only == "":
            return None
        if not _COUNTER_PATTERN.fullmatch(digits_only):
            raise ValueError("شمارنده باید مطابق الگوی YY357#### یا YY373#### باشد")
        return digits_only

    @computed_field
    @property
    def student_type(self) -> int:
        """Return 1 for students in special schools, otherwise 0."""

        school_code = self.school_code
        special_schools = self.SPECIAL_SCHOOLS
        if school_code is None:
            return 0
        return 1 if school_code in special_schools else 0

    def is_assignable(self) -> bool:
        """Determine if the student can be allocated to a mentor."""

        return self.reg_status in {0, 1, 3}

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dictionary excluding computed fields."""

        return self.model_dump(
            by_alias=True,
            exclude={"student_type"},
            exclude_none=True,
        )


def test_special_school_student_type() -> None:
    """Ensure student_type reflects membership in SPECIAL_SCHOOLS."""

    Student.SPECIAL_SCHOOLS = frozenset({283})
    student = Student(
        national_id="0012345679",
        gender=1,
        edu_status=1,
        reg_center=0,
        reg_status=0,
        group_code=3,
        school_code=283,
        mobile="09123456789",
    )
    assert student.student_type == 1
    assert student.is_assignable() is True


def test_school_code_normalization_zero_values() -> None:
    """Zero-like school codes should result in student_type equal to 0."""

    Student.SPECIAL_SCHOOLS = frozenset({283})
    student = Student(
        national_id="0012345679",
        gender=0,
        edu_status=0,
        reg_center=1,
        reg_status=1,
        group_code=2,
        school_code="0",
        mobile="09123456789",
    )
    assert student.school_code is None
    assert student.student_type == 0


def test_school_code_empty_string_results_in_general_student_type() -> None:
    """Empty school codes normalize to None without flagging special type."""

    Student.SPECIAL_SCHOOLS = frozenset({283})
    student = Student(
        national_id="0012345679",
        gender=0,
        edu_status=0,
        reg_center=1,
        reg_status=1,
        group_code=2,
        school_code="",
        mobile="09123456789",
    )
    assert student.school_code is None
    assert student.student_type == 0


def test_mobile_normalization_and_counter_validation() -> None:
    """Validate mobile normalization and counter pattern constraints."""

    Student.SPECIAL_SCHOOLS = frozenset()
    student = Student(
        national_id="1000000001",
        gender=1,
        edu_status=1,
        reg_center=2,
        reg_status=3,
        group_code=4,
        school_code=None,
        mobile="+98۹۱۲۳۴۵۶۷۸۹",
        counter="543571234",
    )
    assert student.mobile == "09123456789"
    assert student.counter == "543571234"
    assert student.is_assignable() is True

    invalid_counter = {
        "national_id": "0034567891",
        "gender": 1,
        "edu_status": 1,
        "reg_center": 1,
        "reg_status": 0,
        "group_code": 5,
        "school_code": None,
        "mobile": "09121234567",
        "counter": "543361234",
    }
    try:
        Student(**invalid_counter)
    except ValidationError as error:
        assert "شمارنده" in str(error)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected ValidationError for invalid counter")


def test_mobile_normalization_accepts_double_zero_prefix() -> None:
    """Ensure 0098-prefixed numbers normalize to the local format."""

    Student.SPECIAL_SCHOOLS = frozenset()
    student = Student(
        national_id="1000000011",
        gender=0,
        edu_status=1,
        reg_center=1,
        reg_status=1,
        group_code=6,
        school_code=None,
        mobile="00989121234567",
    )
    assert student.mobile == "09121234567"


def test_mobile_normalization_with_mixed_persian_digits() -> None:
    """Ensure Persian digits and international prefix normalize correctly."""

    Student.SPECIAL_SCHOOLS = frozenset()
    student = Student(
        national_id="1000000028",
        gender=0,
        edu_status=1,
        reg_center=1,
        reg_status=1,
        group_code=6,
        school_code=None,
        mobile="0098۹۱۲۳۴۵۶۷۸۹",
    )
    assert student.mobile == "09123456789"


def test_national_id_checksum_validation() -> None:
    """Invalid national IDs should raise a Persian error message."""

    Student.SPECIAL_SCHOOLS = frozenset()

    try:
        Student(
            national_id="1111111111",
            gender=1,
            edu_status=1,
            reg_center=0,
            reg_status=0,
            group_code=1,
            school_code=None,
            mobile="09123456789",
        )
    except ValidationError as error:
        assert "کد ملی نامعتبر است" in str(error)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected ValidationError for invalid national ID")


def test_serialization_excludes_none_and_uses_aliases() -> None:
    """Serialized output should rely on Persian aliases and drop None fields."""

    Student.SPECIAL_SCHOOLS = frozenset({283})
    student = Student(
        national_id="0012345679",
        gender=1,
        edu_status=1,
        reg_center=0,
        reg_status=3,
        group_code=2,
        school_code=None,
        mobile="09123456789",
    )
    data = student.to_dict()
    assert "student_type" not in data
    assert "مدرسه نهایی" not in data
    assert "کد مدرسه" not in data
    assert data["کدملی"] == "0012345679"
    assert data["جنسیت"] == 1


def test_school_code_persian_alias_enables_special_student_type() -> None:
    """The new Persian alias should populate the field and student type."""

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
    """Empty strings via the new alias should normalize to None in serialization."""

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


if __name__ == "__main__":  # pragma: no cover - manual execution
    import pytest

    raise SystemExit(pytest.main([__file__]))
