"""Mentor domain model for the Iranian mentor allocation system."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Protocol

import re
from persiantools import characters, digits
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    computed_field,
    field_validator,
)


_MOBILE_PATTERN = re.compile(r"^09\d{9}$")
_NATIONAL_ID_PATTERN = re.compile(r"^\d{10}$")


class MentorType(str, Enum):
    """Permissible mentor categories."""

    NORMAL = "عادی"
    SCHOOL = "مدرسه"


class AvailabilityStatus(str, Enum):
    """Operational availability for mentor allocation."""

    AVAILABLE = "آماده"
    FULL = "پر"
    INACTIVE = "غیرفعال"


class StudentLike(Protocol):
    """Protocol describing the minimal student attributes required."""

    gender: int
    edu_status: int
    student_type: int
    group_code: int
    school_code: Optional[int]


def _normalize_name(value: str) -> str:
    """Normalize Persian names by unifying script and spaces."""

    normalized = characters.ar_to_fa(value or "")
    normalized = " ".join(normalized.split())
    return normalized


def _normalize_mobile(value: Optional[str]) -> Optional[str]:
    """Normalize Iranian mobile numbers to the 09XXXXXXXXX pattern."""

    if value is None:
        return None
    digits_only = digits.fa_to_en(digits.ar_to_fa(str(value).strip()))
    digits_only = re.sub(r"\D", "", digits_only)
    if digits_only.startswith("+98"):
        digits_only = "0" + digits_only[3:]
    elif digits_only.startswith("98"):
        digits_only = "0" + digits_only[2:]
    if digits_only.startswith("9") and len(digits_only) == 10:
        digits_only = "0" + digits_only
    if not digits_only.startswith("0") and digits_only:
        digits_only = "0" + digits_only
    return digits_only


def _validate_national_id(code: str) -> bool:
    """Validate Iranian national identification numbers."""

    if not _NATIONAL_ID_PATTERN.match(code):
        return False
    digits_list = [int(char) for char in code]
    checksum = digits_list[-1]
    total = sum(digits_list[i] * (10 - i) for i in range(9))
    remainder = total % 11
    expected = remainder if remainder < 2 else 11 - remainder
    return checksum == expected


class Mentor(BaseModel):
    """Mentor entity with validation aligned to allocation core rules."""

    mentor_id: int = Field(..., alias="id", description="شناسهٔ منتور")
    first_name: str = Field(..., description="نام")
    last_name: str = Field(..., description="نام خانوادگی")
    gender: int = Field(..., description="جنسیت: ۰ برای خانم، ۱ برای آقا")
    mentor_type: MentorType = Field(..., description="نوع منتور")
    special_schools: List[int] = Field(
        default_factory=list, description="کد مدارس تحت پوشش (حداکثر ۴)"
    )
    capacity: int = Field(
        default=60,
        alias="max_students",
        description="ظرفیت کل",
    )
    current_load: int = Field(
        default=0,
        alias="current_assignments",
        ge=0,
        description="تعداد تخصیص‌های فعلی",
    )
    allowed_groups: List[int] = Field(
        default_factory=list,
        alias="subject_areas",
        description="گروه‌های مجاز",
    )
    manager_name: Optional[str] = Field(None, description="مدیر مستقیم")
    is_active: bool = Field(default=True, description="وضعیت فعال بودن")
    availability_status: AvailabilityStatus = Field(
        default=AvailabilityStatus.AVAILABLE,
        description="وضعیت دسترس‌پذیری",
    )
    mobile: Optional[str] = Field(None, description="شمارهٔ موبایل")
    email: Optional[EmailStr] = Field(None, description="ایمیل سازمانی")
    national_id: Optional[str] = Field(None, description="کد ملی منتور")

    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
        str_strip_whitespace=True,
        populate_by_name=True,
        use_enum_values=True,
    )

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def _normalize_names(cls, value: str) -> str:
        normalized = _normalize_name(str(value))
        if not normalized:
            raise ValueError("نام و نام خانوادگی باید مقدار داشته باشند.")
        return normalized

    @field_validator("manager_name", mode="before")
    @classmethod
    def _normalize_manager(cls, value: Optional[str]) -> Optional[str]:
        if value in {None, ""}:
            return None
        normalized = _normalize_name(str(value))
        return normalized or None

    @field_validator("gender")
    @classmethod
    def _validate_gender(cls, value: int) -> int:
        if value not in {0, 1}:
            raise ValueError("جنسیت باید یکی از مقادیر {۰، ۱} باشد.")
        return value

    @field_validator("special_schools")
    @classmethod
    def _validate_special_schools(cls, value: List[int]) -> List[int]:
        if len(value) > 4:
            raise ValueError("حداکثر چهار مدرسه می‌تواند تعریف شود.")
        cleaned: List[int] = []
        for code in value:
            if not isinstance(code, int) or code <= 0:
                raise ValueError("کد مدرسه باید عدد صحیح مثبت باشد.")
            cleaned.append(code)
        return cleaned

    @field_validator("capacity")
    @classmethod
    def _validate_capacity(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("ظرفیت باید بزرگ‌تر از صفر باشد.")
        return value

    @field_validator("current_load")
    @classmethod
    def _validate_current_load(cls, value: int, info) -> int:
        if value < 0:
            raise ValueError("تعداد تخصیص فعلی نمی‌تواند منفی باشد.")
        capacity = info.data.get("capacity", 60)
        if value > capacity:
            raise ValueError("تعداد تخصیص فعلی نباید از ظرفیت بیشتر باشد.")
        return value

    @field_validator("allowed_groups")
    @classmethod
    def _validate_allowed_groups(cls, value: List[int]) -> List[int]:
        for code in value:
            if not isinstance(code, int) or code < 0:
                raise ValueError("کد گروه باید عدد صحیح نامنفی باشد.")
        return value

    @field_validator("mobile", mode="before")
    @classmethod
    def _normalize_mobile_before(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_mobile(value)

    @field_validator("mobile")
    @classmethod
    def _validate_mobile(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not _MOBILE_PATTERN.match(value):
            raise ValueError("شمارهٔ موبایل نامعتبر است. فرمت مجاز: 09XXXXXXXXX")
        return value

    @field_validator("national_id", mode="before")
    @classmethod
    def _normalize_national_id(cls, value: Optional[str]) -> Optional[str]:
        if value in {None, ""}:
            return None
        cleaned = digits.fa_to_en(digits.ar_to_fa(str(value).strip()))
        cleaned = re.sub(r"\D", "", cleaned)
        return cleaned or None

    @field_validator("national_id")
    @classmethod
    def _validate_national_id_field(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not _validate_national_id(value):
            raise ValueError("کد ملی نامعتبر است.")
        return value

    @computed_field
    @property
    def display_name(self) -> str:
        """نام نمایشی منتور."""

        return f"{self.first_name} {self.last_name}".strip()

    @computed_field
    @property
    def capacity_remaining(self) -> int:
        """ظرفیت باقیمانده بر اساس ظرفیت و بار جاری."""

        remaining = self.capacity - self.current_load
        return remaining if remaining > 0 else 0

    @computed_field
    @property
    def mentor_code(self) -> str:
        """کد نمایشی استاندارد."""

        return f"M{int(self.mentor_id):06d}"

    def can_accept_student(self, student: StudentLike) -> bool:
        """Determine if the mentor can accept the provided student."""

        if not self.is_active or self.availability_status in {
            AvailabilityStatus.FULL,
            AvailabilityStatus.INACTIVE,
        }:
            return False
        if self.current_load >= self.capacity:
            return False
        if self.gender != getattr(student, "gender", None):
            return False
        allowed_groups = set(self.allowed_groups)
        if getattr(student, "group_code", None) not in allowed_groups:
            return False

        is_graduate = getattr(student, "edu_status", None) == 0
        student_type = getattr(student, "student_type", None)

        if self.mentor_type == MentorType.SCHOOL:
            if is_graduate:
                return False
            if student_type != 1:
                return False
            student_school = getattr(student, "school_code", None)
            special_schools = set(self.special_schools)
            if student_school is None or student_school not in special_schools:
                return False
        else:
            if student_type == 1:
                return False

        return True

    def get_workload_percentage(self) -> float:
        """Return workload as a percentage with two decimal precision."""

        if self.capacity <= 0:
            return 0.0
        return round((self.current_load / float(self.capacity)) * 100.0, 2)


__all__ = ["Mentor", "MentorType", "AvailabilityStatus", "StudentLike"]
