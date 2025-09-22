"""Mentor domain model for the Iranian mentor allocation system."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from enum import Enum
from typing import Any, FrozenSet, Optional, Protocol

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    computed_field,
    field_validator,
)


from .mentor_legacy_helpers import (
    _encode_collections as _legacy_encode_collections,
    _normalize_code_collection as _legacy_normalize_code_collection,
    _normalize_int as _legacy_normalize_int,
    _normalize_optional_int as _legacy_normalize_optional_int,
)


_MOBILE_PATTERN = re.compile(r"^09\d{9}$")
_NATIONAL_ID_PATTERN = re.compile(r"^\d{10}$")

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

_ARABIC_TO_PERSIAN_CHARACTERS = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ﻱ": "ی",
        "ﻲ": "ی",
        "ﻳ": "ی",
        "ك": "ک",
        "ﻙ": "ک",
        "ﻛ": "ک",
        "ﻜ": "ک",
        "ة": "ه",
        "ۀ": "هٔ",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "ٱ": "ا",
    }
)


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

    text = unicodedata.normalize("NFKC", value or "")
    normalized = text.translate(_ARABIC_TO_PERSIAN_CHARACTERS)
    normalized = " ".join(normalized.split())
    return normalized


def _normalize_mobile(value: Optional[str]) -> Optional[str]:
    """Normalize Iranian mobile numbers to the 09XXXXXXXXX pattern."""

    if value is None:
        return None
    digits_only = unicodedata.normalize("NFKC", str(value).strip())
    digits_only = digits_only.translate(_DIGIT_TRANSLATION)
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
    special_schools: FrozenSet[int] = Field(
        default_factory=frozenset, description="کد مدارس تحت پوشش (حداکثر ۴)"
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
    allowed_groups: FrozenSet[int] = Field(
        default_factory=frozenset,
        alias="subject_areas",
        description="گروه‌های مجاز",
    )
    manager_id: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices(
            "manager_id",
            "شناسه مدیر",
            "شناسهٔ مدیر",
            "شناسه‌ٔ مدیر",
        ),
        description="شناسهٔ مدیر مرتبط در سامانه",
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

    @field_validator("special_schools", mode="before")
    @classmethod
    def _normalize_special_schools(cls, value: Any) -> FrozenSet[int]:
        if value in (None, ""):
            return frozenset()
        if isinstance(value, str):
            raw_items = [value]
        elif isinstance(value, Iterable):
            raw_items = list(value)
        else:
            raw_items = [value]
        if len(raw_items) > 4:
            raise ValueError("حداکثر چهار مدرسه می‌تواند تعریف شود.")
        cleaned: list[int] = []
        for code in raw_items:
            try:
                normalized = unicodedata.normalize("NFKC", str(code).strip())
                normalized = normalized.translate(_DIGIT_TRANSLATION)
                number = int(normalized)
            except (TypeError, ValueError):
                raise ValueError("کد مدرسه باید عدد صحیح مثبت باشد.") from None
            if number <= 0:
                raise ValueError("کد مدرسه باید عدد صحیح مثبت باشد.")
            cleaned.append(number)
        return frozenset(cleaned)

    @field_validator("special_schools")
    @classmethod
    def _validate_special_schools(cls, value: FrozenSet[int]) -> FrozenSet[int]:
        if len(value) > 4:
            raise ValueError("حداکثر چهار مدرسه می‌تواند تعریف شود.")
        return value

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

    @field_validator("allowed_groups", mode="before")
    @classmethod
    def _normalize_allowed_groups(cls, value: Any) -> FrozenSet[int]:
        if value in (None, ""):
            return frozenset()
        if isinstance(value, str):
            raw_items = [value]
        elif isinstance(value, Iterable):
            raw_items = list(value)
        else:
            raw_items = [value]
        cleaned: list[int] = []
        for code in raw_items:
            try:
                normalized = unicodedata.normalize("NFKC", str(code).strip())
                normalized = normalized.translate(_DIGIT_TRANSLATION)
                number = int(normalized)
            except (TypeError, ValueError):
                raise ValueError("کد گروه باید عدد صحیح نامنفی باشد.") from None
            if number < 0:
                raise ValueError("کد گروه باید عدد صحیح نامنفی باشد.")
            cleaned.append(number)
        return frozenset(cleaned)

    @field_validator("allowed_groups")
    @classmethod
    def _validate_allowed_groups(cls, value: FrozenSet[int]) -> FrozenSet[int]:
        return value

    @field_validator("manager_id", mode="before")
    @classmethod
    def _normalize_manager_id(cls, value: Any) -> Optional[int]:
        if value in {None, ""}:
            return None
        try:
            normalized = unicodedata.normalize("NFKC", str(value).strip())
            normalized = normalized.translate(_DIGIT_TRANSLATION)
            if normalized == "":
                return None
            manager_id = int(normalized)
        except (TypeError, ValueError):
            raise ValueError("شناسهٔ مدیر باید عدد صحیح نامنفی باشد.") from None
        if manager_id < 0:
            raise ValueError("شناسهٔ مدیر باید عدد صحیح نامنفی باشد.")
        return manager_id

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
        cleaned = unicodedata.normalize("NFKC", str(value).strip())
        cleaned = cleaned.translate(_DIGIT_TRANSLATION)
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
        if getattr(student, "group_code", None) not in self.allowed_groups:
            return False

        is_graduate = getattr(student, "edu_status", None) == 0
        student_type = getattr(student, "student_type", None)

        if self.mentor_type == MentorType.SCHOOL:
            if is_graduate:
                return False
            if student_type != 1:
                return False
            student_school = getattr(student, "school_code", None)
            if student_school is None or student_school not in self.special_schools:
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

    def to_dict(
        self,
        *,
        by_alias: bool = True,
        exclude_none: bool = True,
    ) -> dict[str, Any]:
        """Return a JSON-friendly dictionary representation.

        Parameters
        ----------
        by_alias:
            If ``True``, field aliases such as ``max_students`` are used.
        exclude_none:
            When ``True``, keys with ``None`` values are omitted from the output.

        Returns
        -------
        dict[str, Any]
            A dictionary safe for JSON serialization with sets converted to
            sorted lists.
        """

        data = self.model_dump(by_alias=by_alias, exclude_none=exclude_none)
        return _encode_collections(data)


# Legacy helper compatibility -------------------------------------------------

_normalize_int = _legacy_normalize_int
_normalize_optional_int = _legacy_normalize_optional_int
_normalize_code_collection = _legacy_normalize_code_collection


def normalize_iterable_to_int_set(value: Any, field_title: str) -> FrozenSet[int]:
    """Normalize an iterable of codes into a frozen set of integers."""

    return _legacy_normalize_code_collection(value, field_title)


def normalize_mapping_to_int_set(value: Any, field_title: str) -> FrozenSet[int]:
    """Normalize a mapping of codes into a frozen set of enabled integer keys."""

    return _legacy_normalize_code_collection(value, field_title)


_encode_collections = _legacy_encode_collections


__all__ = (
    "AvailabilityStatus",
    "Mentor",
    "MentorType",
    # stable helper exports
    "normalize_iterable_to_int_set",
    "normalize_mapping_to_int_set",
    "_encode_collections",
)
