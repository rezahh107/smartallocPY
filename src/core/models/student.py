"""Student model with Iranian normalization and validation rules."""

from __future__ import annotations

from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
)

from ..special_schools import get_special_schools
from .constants import (
    EDU_STATUS_CODES,
    GENDER_CODES,
    REG_CENTER_CODES,
    REG_STATUS_CODES,
)
from .shared_normalize import (
    canonicalize_mobile,
    canonicalize_national_id,
    parse_int,
    validate_iran_national_id,
)

_MOBILE_ERROR = "شماره موبایل باید با 09 شروع شده و ۱۱ رقم باشد"
_NATIONAL_ID_LENGTH_ERROR = "کد ملی باید دقیقاً ۱۰ رقم باشد"
_NATIONAL_ID_INVALID_ERROR = "کد ملی نامعتبر است"
_GENDER_ERROR = "جنسیت باید یکی از مقادیر {۰، ۱} باشد"
_EDU_STATUS_ERROR = "وضعیت تحصیلی باید یکی از مقادیر {۰، ۱} باشد"
_REG_STATUS_ERROR = "وضعیت ثبت نام باید یکی از مقادیر {۰، ۱، ۳} باشد"
_REG_CENTER_ERROR = "مرکز ثبت نام باید یکی از مقادیر {۰، ۱، ۲} باشد"
_GROUP_CODE_ERROR = "کد گروه باید بزرگتر از صفر باشد"
_SCHOOL_CODE_ERROR = "کد مدرسه باید عددی مثبت باشد"


class Student(BaseModel):
    """Validated representation of a student record used for allocation.

    Examples:
        >>> Student.model_validate({
        ...     "nationalCode": "0012345675",
        ...     "mobilePhone": "+98 912 345 6789",
        ...     "genderCode": "۱",
        ...     "reg_status": "۱",
        ...     "center": "۱",
        ...     "edu_status": "۱",
        ...     "grp": "۲۲",
        ...     "schoolId": "۲۸۳",
        ... })
        Student(national_id='0012345675', mobile='09123456789', ...)
    """

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    national_id: str = Field(
        ...,
        validation_alias=AliasChoices(
            "national_id",
            "nationalCode",
            "nationalId",
            "کدملی",
            "کد ملی",
        ),
        description="کد ملی ۱۰ رقمی",
    )
    mobile: str = Field(
        ...,
        validation_alias=AliasChoices(
            "mobile",
            "mobilePhone",
            "mobile_phone",
            "mobile_number",
            "شماره موبایل",
            "شماره همراه",
        ),
        description="شماره موبایل استاندارد ۰۹XXXXXXXXX",
    )
    gender: int = Field(
        ...,
        validation_alias=AliasChoices("gender", "genderCode", "جنسیت"),
        description="کد جنسیت (۰ یا ۱)",
    )
    reg_status: int = Field(
        ...,
        validation_alias=AliasChoices("reg_status", "regStatus", "وضعیت ثبت نام"),
        description="وضعیت مجاز بودن برای تخصیص",
    )
    reg_center: int = Field(
        ...,
        validation_alias=AliasChoices("reg_center", "center", "مرکز"),
        description="مرکز ثبت نام (۰، ۱، ۲)",
    )
    edu_status: int = Field(
        ...,
        validation_alias=AliasChoices("edu_status", "eduStatus", "وضعیت تحصیلی"),
        description="وضعیت تحصیلی (۰ فارغ التحصیل، ۱ در حال تحصیل)",
    )
    group_code: int = Field(
        ...,
        validation_alias=AliasChoices("group_code", "group", "grp", "گروه آزمایشی"),
        description="کد گروه آموزشی مثبت",
    )
    school_code: int | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "school_code",
            "schoolId",
            "sch_code",
            "school",
            "کد مدرسه",
        ),
        description="کد مدرسه ویژه در صورت وجود",
    )

    @field_validator("national_id", mode="before")
    @classmethod
    def _normalize_national_id(cls, value: Any) -> str:
        """Normalize national IDs before checksum validation.

        Args:
            value: Raw national ID which may contain Persian digits.

        Returns:
            str: Canonical ten-digit national ID.

        Raises:
            ValueError: If normalization fails.
        """

        return canonicalize_national_id(value, error_message=_NATIONAL_ID_LENGTH_ERROR)

    @field_validator("national_id")
    @classmethod
    def _validate_national_id(cls, value: str) -> str:
        """Enforce the Iranian checksum and uniqueness constraints.

        Args:
            value: Canonical national ID value.

        Returns:
            str: The validated national ID.

        Raises:
            ValueError: If the checksum or digit pattern is invalid.
        """

        if not validate_iran_national_id(value):
            raise ValueError(_NATIONAL_ID_INVALID_ERROR)
        return value

    @field_validator("mobile", mode="before")
    @classmethod
    def _normalize_mobile(cls, value: Any) -> str:
        """Canonicalize Iranian mobile numbers to ``09XXXXXXXXX``.

        Args:
            value: Raw mobile number.

        Returns:
            str: Canonical Iranian mobile number.

        Raises:
            ValueError: If the number is invalid.
        """

        return canonicalize_mobile(value, _MOBILE_ERROR)

    @field_validator("gender", mode="before")
    @classmethod
    def _normalize_gender(cls, value: Any) -> int:
        """Ensure gender codes match the approved enumeration."""

        return int(
            parse_int(
                value,
                error_message=_GENDER_ERROR,
                allowed_values=GENDER_CODES,
            )
        )

    @field_validator("edu_status", mode="before")
    @classmethod
    def _normalize_edu_status(cls, value: Any) -> int:
        return int(
            parse_int(
                value,
                error_message=_EDU_STATUS_ERROR,
                allowed_values=EDU_STATUS_CODES,
            )
        )

    @field_validator("reg_status", mode="before")
    @classmethod
    def _normalize_reg_status(cls, value: Any) -> int:
        return int(
            parse_int(
                value,
                error_message=_REG_STATUS_ERROR,
                allowed_values=REG_STATUS_CODES,
            )
        )

    @field_validator("reg_center", mode="before")
    @classmethod
    def _normalize_reg_center(cls, value: Any) -> int:
        return int(
            parse_int(
                value,
                error_message=_REG_CENTER_ERROR,
                allowed_values=REG_CENTER_CODES,
            )
        )

    @field_validator("group_code", mode="before")
    @classmethod
    def _normalize_group_code(cls, value: Any) -> int:
        return int(
            parse_int(
                value,
                error_message=_GROUP_CODE_ERROR,
                positive_only=True,
            )
        )

    @field_validator("school_code", mode="before")
    @classmethod
    def _normalize_school_code(cls, value: Any) -> int | None:
        if value in {None, "", "0", 0}:
            return None
        parsed = parse_int(
            value,
            error_message=_SCHOOL_CODE_ERROR,
            positive_only=True,
            allow_none=True,
        )
        return int(parsed) if parsed is not None else None

    @computed_field
    @property
    def student_type(self) -> int:
        """Return ``1`` when the student attends a configured special school.

        Returns:
            int: ``1`` for special-school students, otherwise ``0``.
        """

        school_code = self.school_code
        if school_code is None:
            return 0
        special_schools = get_special_schools()
        return 1 if school_code in special_schools else 0

    def is_assignable(self) -> bool:
        """Return ``True`` when the student registration status permits allocation.

        Returns:
            bool: ``True`` if the registration status is among allowed values.
        """

        return self.reg_status in REG_STATUS_CODES


__all__ = ["Student"]
