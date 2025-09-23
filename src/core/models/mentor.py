"""Mentor model with deterministic eligibility and normalization rules."""

from __future__ import annotations

from enum import Enum
from typing import Any, FrozenSet, Optional, Protocol

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_serializer,
    field_validator,
    model_validator,
)

from .constants import GENDER_CODES, REG_CENTER_CODES
from .shared_normalize import (
    canonicalize_mobile,
    canonicalize_national_id,
    frozenset_of_ints,
    parse_int,
    validate_iran_national_id,
)

_MOBILE_ERROR = "شماره موبایل باید با 09 شروع شده و ۱۱ رقم باشد"
_NATIONAL_ID_LENGTH_ERROR = "کد ملی باید دقیقاً ۱۰ رقم باشد"
_NATIONAL_ID_INVALID_ERROR = "کد ملی نامعتبر است"
_GROUP_SET_ERROR = "لیست گروه‌های مجاز نمی‌تواند خالی باشد"
_GROUP_ITEM_ERROR = "کد گروه باید عدد صحیح مثبت باشد"
_CENTER_SET_ERROR = "لیست مراکز مجاز نمی‌تواند خالی باشد"
_CENTER_ITEM_ERROR = "مرکز مجاز باید یکی از {۰، ۱، ۲} باشد"
_SPECIAL_SCHOOL_ERROR = "منتور مدرسه باید حداقل یک مدرسه ویژه داشته باشد"
_SPECIAL_SCHOOL_LIMIT_ERROR = "حداکثر چهار مدرسه ویژه مجاز است"
_CAPACITY_ERROR = "ظرفیت باید عدد صحیح بدون علامت باشد"
_CURRENT_LOAD_ERROR = "تعداد تخصیص‌ها نمی‌تواند از ظرفیت بیشتر باشد"
_GENDER_ERROR = "جنسیت باید یکی از مقادیر {۰، ۱} باشد"


class MentorType(str, Enum):
    """Enumeration describing mentor categories."""

    NORMAL = "عادی"
    SCHOOL = "مدرسه"


class AvailabilityStatus(str, Enum):
    """Enumeration describing mentor availability states."""

    AVAILABLE = "آماده"
    FULL = "پر"
    INACTIVE = "غیرفعال"


class StudentLike(Protocol):
    """Protocol describing student attributes needed by mentors."""

    gender: int
    edu_status: int
    student_type: int
    group_code: int
    school_code: Optional[int]
    reg_center: int


class Mentor(BaseModel):
    """Mentor entity aligned with allocation eligibility requirements.

    Examples:
        >>> Mentor.model_validate({
        ...     "mentor_id": 1001,
        ...     "first_name": "زهرا",
        ...     "last_name": "احمدی",
        ...     "gender": "۱",
        ...     "type": "عادی",
        ...     "allowed_groups": ["۲۲", "۲۵"],
        ...     "allowed_centers": [0, 1],
        ...     "mobile": "+989123456789",
        ...     "national_id": "1234567891",
        ... })
        Mentor(mentor_id=1001, first_name='زهرا', last_name='احمدی', ...)
    """

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        json_encoders={frozenset: lambda value: sorted(value)},
    )

    mentor_id: int = Field(..., validation_alias=AliasChoices("mentor_id", "id"), description="شناسه منتور")
    first_name: str = Field(..., description="نام")
    last_name: str = Field(..., description="نام خانوادگی")
    gender: int = Field(..., description="جنسیت منتور")
    mentor_type: MentorType = Field(
        ..., validation_alias=AliasChoices("mentor_type", "type"), description="نوع منتور"
    )
    alias_code: str | None = Field(
        default=None,
        validation_alias=AliasChoices("alias_code", "alias", "aliasCode", "کد مستعار"),
        description="کد مستعار اختیاری",
    )
    special_schools: FrozenSet[int] = Field(
        default_factory=frozenset,
        validation_alias=AliasChoices("special_schools", "specialSchools", "schools", "school_codes"),
        description="مدارس ویژه تحت پوشش منتور مدرسه",
    )
    allowed_groups: FrozenSet[int] = Field(
        ..., validation_alias=AliasChoices("allowed_groups", "grp", "groups"), description="گروه‌های مجاز"
    )
    allowed_centers: FrozenSet[int] = Field(
        ..., validation_alias=AliasChoices("allowed_centers", "centers", "allowedCenters", "center"), description="مراکز مجاز"
    )
    capacity: int = Field(
        default=60,
        validation_alias=AliasChoices("capacity", "max_students"),
        description="ظرفیت کل",
    )
    current_load: int = Field(
        default=0,
        validation_alias=AliasChoices("current_load", "current_assignments"),
        description="تخصیص فعلی",
    )
    mobile: str = Field(..., description="شماره موبایل منتور")
    national_id: str = Field(..., description="کد ملی منتور")
    is_active: bool = Field(default=True, description="وضعیت فعال بودن")
    availability_status: AvailabilityStatus = Field(
        default=AvailabilityStatus.AVAILABLE,
        description="وضعیت دسترس‌پذیری منتور",
    )

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def _normalize_names(cls, value: Any) -> str:
        """Strip whitespace and ensure names are present."""

        if value in {None, ""}:
            raise ValueError("نام و نام خانوادگی الزامی است")
        return str(value).strip()

    @field_validator("gender", mode="before")
    @classmethod
    def _normalize_gender(cls, value: Any) -> int:
        """Validate mentor gender codes using shared constants."""

        return int(parse_int(value, error_message=_GENDER_ERROR, allowed_values=GENDER_CODES))

    @field_validator("mobile", mode="before")
    @classmethod
    def _normalize_mobile(cls, value: Any) -> str:
        """Normalize mentor mobile numbers to the canonical format."""

        return canonicalize_mobile(value, _MOBILE_ERROR)

    @field_validator("national_id", mode="before")
    @classmethod
    def _normalize_national_id(cls, value: Any) -> str:
        """Normalize mentor national IDs to ten ASCII digits."""

        return canonicalize_national_id(value, error_message=_NATIONAL_ID_LENGTH_ERROR)

    @field_validator("national_id")
    @classmethod
    def _validate_national_id(cls, value: str) -> str:
        """Validate mentor national IDs using the Iranian checksum."""

        if not validate_iran_national_id(value):
            raise ValueError(_NATIONAL_ID_INVALID_ERROR)
        return value

    @field_validator("allowed_groups", mode="before")
    @classmethod
    def _normalize_allowed_groups(cls, value: Any) -> FrozenSet[int]:
        """Convert raw group inputs to a validated frozenset."""

        return frozenset_of_ints(
            value,
            error_message=_GROUP_SET_ERROR,
            item_error_message=_GROUP_ITEM_ERROR,
            positive_only=True,
            allow_empty=False,
        )

    @field_validator("allowed_centers", mode="before")
    @classmethod
    def _normalize_allowed_centers(cls, value: Any) -> FrozenSet[int]:
        """Convert raw center inputs to a validated frozenset."""

        return frozenset_of_ints(
            value,
            error_message=_CENTER_SET_ERROR,
            item_error_message=_CENTER_ITEM_ERROR,
            positive_only=False,
            allow_empty=False,
            allowed_values=REG_CENTER_CODES,
        )

    @field_validator("special_schools", mode="before")
    @classmethod
    def _normalize_special_schools(cls, value: Any) -> FrozenSet[int]:
        """Normalize optional special-school codes to positive integers."""

        return frozenset_of_ints(
            value,
            error_message="لیست مدارس ویژه نمی‌تواند خالی باشد",
            item_error_message="کد مدرسه باید عددی مثبت باشد",
            positive_only=True,
            allow_empty=True,
        )

    @field_validator("capacity", mode="before")
    @classmethod
    def _normalize_capacity(cls, value: Any) -> int:
        """Normalize mentor capacity while applying defaults."""

        if value in {None, ""}:
            return 60
        number = parse_int(value, error_message=_CAPACITY_ERROR, minimum=0)
        return int(number)

    @field_validator("current_load", mode="before")
    @classmethod
    def _normalize_current_load(cls, value: Any) -> int:
        """Normalize the mentor's current load ensuring non-negativity."""

        if value in {None, ""}:
            return 0
        number = parse_int(value, error_message=_CAPACITY_ERROR, minimum=0)
        return int(number)

    @field_validator("alias_code", mode="before")
    @classmethod
    def _normalize_alias(cls, value: Any) -> str | None:
        """Strip alias codes and treat blanks as ``None``."""

        if value in {None, ""}:
            return None
        return str(value).strip()

    @field_serializer("allowed_groups", "allowed_centers", when_used="always")
    def _serialize_sets(self, value: FrozenSet[int]) -> list[int]:
        """Serialize frozenset fields as sorted lists for deterministic output."""

        return sorted(value)

    @model_validator(mode="after")
    def _post_init_checks(self) -> "Mentor":
        """Enforce cross-field invariants after model validation."""

        if self.current_load > self.capacity:
            raise ValueError(_CURRENT_LOAD_ERROR)
        if self.mentor_type is MentorType.SCHOOL:
            if not self.special_schools:
                raise ValueError(_SPECIAL_SCHOOL_ERROR)
        if len(self.special_schools) > 4:
            raise ValueError(_SPECIAL_SCHOOL_LIMIT_ERROR)
        return self

    @computed_field
    @property
    def display_name(self) -> str:
        """Return a human-friendly representation of the mentor's name."""

        return f"{self.first_name} {self.last_name}".strip()

    @computed_field
    @property
    def capacity_remaining(self) -> int:
        """Return remaining capacity ensuring non-negative output."""

        remaining = self.capacity - self.current_load
        return remaining if remaining > 0 else 0

    def can_accept_student(self, student: StudentLike) -> bool:
        """Return ``True`` when mentor eligibility constraints pass.

        Args:
            student: Student-like object exposing allocation attributes.

        Returns:
            bool: ``True`` if the mentor can accept the student.
        """

        if not self.is_active or self.availability_status is not AvailabilityStatus.AVAILABLE:
            return False
        if student.reg_center not in self.allowed_centers:
            return False
        if self.mentor_type is MentorType.SCHOOL:
            if student.student_type != 1:
                return False
            if student.school_code is None or student.school_code not in self.special_schools:
                return False
            if student.edu_status == 0:
                return False
        else:
            if student.student_type == 1:
                return False
        if student.group_code not in self.allowed_groups:
            return False
        if self.current_load >= self.capacity:
            return False
        if student.gender != self.gender:
            return False
        return True


__all__ = ["Mentor", "MentorType", "StudentLike"]
