"""Phase 1 Mentor model with localized validation and serialization.

This module defines a standalone Pydantic v2 model named :class:`Mentor` that
matches the phase 1 specification. The model offers full validation,
normalization helpers, computed properties, and localized error messages.
Minimal pytest-based unit tests are embedded at the end of the file, alongside
an executable entry-point for convenience.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any, FrozenSet, Optional

import pytest

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    computed_field,
    field_validator,
    model_validator,
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
_NON_DIGIT_RE = re.compile(r"\D+")


def _normalize_int(value: Any, *, allow_zero: bool, field_title: str) -> int:
    """Convert a value to integer while handling localized digits.

    Args:
        value: Incoming raw value.
        allow_zero: Whether ``0`` is a permitted result.
        field_title: Field name used in error messages.

    Returns:
        Normalized integer.

    Raises:
        ValueError: If the value is missing or invalid.
    """

    if value is None:
        raise ValueError(f"{field_title} الزامی است")
    if isinstance(value, bool):
        raise ValueError(f"{field_title} باید عددی باشد")
    if isinstance(value, int):
        result = value
    else:
        text = str(value).strip()
        if not text:
            raise ValueError(f"{field_title} نمی‌تواند خالی باشد")
        digits_only = _NON_DIGIT_RE.sub("", text.translate(_DIGIT_TRANSLATION))
        if not digits_only:
            raise ValueError(f"{field_title} باید شامل ارقام باشد")
        result = int(digits_only)
    if result < 0 or (not allow_zero and result == 0):
        raise ValueError(f"{field_title} باید عددی مثبت باشد")
    return result


def _normalize_optional_int(value: Any, field_title: str) -> Optional[int]:
    """Normalize optional integers, returning ``None`` when unset."""

    if value in {None, "", []}:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field_title} باید عددی باشد")
    try:
        normalized = _normalize_int(value, allow_zero=True, field_title=field_title)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    return normalized


def _normalize_code_collection(value: Any, field_title: str) -> FrozenSet[int]:
    """Normalize iterable code collections into deduplicated frozen sets."""

    if value is None:
        return frozenset()

    if isinstance(value, str):
        if not value.strip():
            return frozenset()
        items = [value]
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        items = list(value)
        if not items:
            return frozenset()
    else:
        items = [value]

    normalized_items = set()
    for item in items:
        if item is None:
            raise ValueError(f"{field_title} نمی‌تواند مقادیر تهی داشته باشد")
        if isinstance(item, str):
            if not item.strip():
                raise ValueError(f"{field_title} نمی‌تواند مقادیر خالی داشته باشد")
        elif isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
            raise ValueError(f"{field_title} باید فقط شامل اعداد ساده باشد")
        if isinstance(item, bool):
            raise ValueError(f"{field_title} باید فقط شامل اعداد باشد")
        normalized = _normalize_int(
            item,
            allow_zero=False,
            field_title=f"مقدار {field_title}",
        )
        normalized_items.add(normalized)
    return frozenset(normalized_items)


class Mentor(BaseModel):
    """Pydantic model capturing mentor attributes with strict validation."""

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        validate_assignment=True,
    )

    mentor_id: int = Field(
        ...,
        validation_alias=AliasChoices("mentor_id", "کد پشتیبان"),
        serialization_alias="کد پشتیبان",
        description="شناسه یکتا برای پشتیبان",
    )
    gender: int = Field(
        ...,
        validation_alias=AliasChoices("gender", "جنسیت"),
        serialization_alias="جنسیت",
        description="کد جنسیت (۰ یا ۱)",
    )
    type: str = Field(
        ...,
        validation_alias=AliasChoices("type", "نوع پشتیبان"),
        serialization_alias="نوع پشتیبان",
        description="نوع پشتیبان (ordinary یا school)",
    )
    capacity: int = Field(
        default=60,
        validation_alias=AliasChoices("capacity", "ظرفیت"),
        serialization_alias="ظرفیت",
        description="ظرفیت کل پشتیبان",
    )
    current_load: int = Field(
        default=0,
        validation_alias=AliasChoices("current_load", "بار جاری"),
        serialization_alias="بار جاری",
        description="تعداد تخصیص های فعلی",
    )
    alias_code: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("alias_code", "کد مستعار"),
        serialization_alias="کد مستعار",
        description="کد مستعار اختیاری",
    )
    manager_id: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("manager_id", "شناسه مدیر"),
        serialization_alias="شناسه مدیر",
        description="شناسه مدیر مربوط",
    )
    allowed_groups: FrozenSet[int] = Field(
        default_factory=frozenset,
        validation_alias=AliasChoices("allowed_groups", "گروه‌های مجاز"),
        serialization_alias="گروه‌های مجاز",
        description="مجموعه کد گروه های مجاز",
    )
    allowed_centers: FrozenSet[int] = Field(
        default_factory=frozenset,
        validation_alias=AliasChoices("allowed_centers", "مراکز مجاز"),
        serialization_alias="مراکز مجاز",
        description="مجموعه کد مراکز مجاز",
    )
    schools: FrozenSet[int] = Field(
        default_factory=frozenset,
        validation_alias=AliasChoices("schools", "مدارس مجاز", "کد مدرسه"),
        serialization_alias="مدارس مجاز",
        description="مدارس تحت پوشش",
    )
    is_active: bool = Field(
        ...,
        validation_alias=AliasChoices("is_active", "فعال"),
        serialization_alias="فعال",
        description="وضعیت فعال بودن پشتیبان",
    )

    @field_validator("mentor_id", mode="before")
    @classmethod
    def _normalize_mentor_id(cls, value: Any) -> int:
        return _normalize_int(value, allow_zero=False, field_title="شناسه پشتیبان")

    @field_validator("gender", mode="before")
    @classmethod
    def _normalize_gender(cls, value: Any) -> int:
        normalized = _normalize_int(value, allow_zero=True, field_title="جنسیت")
        if normalized not in {0, 1}:
            raise ValueError("مقدار جنسیت نامعتبر است")
        return normalized

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_type(cls, value: Any) -> str:
        if value is None:
            raise ValueError("نوع پشتیبان الزامی است")
        text = str(value).strip().lower()
        if text not in {"school", "ordinary"}:
            raise ValueError("مقدار نوع پشتیبان نامعتبر است")
        return text

    @field_validator("capacity", mode="before")
    @classmethod
    def _normalize_capacity(cls, value: Any) -> int:
        normalized_value = value if value is not None else 60
        return _normalize_int(
            normalized_value,
            allow_zero=True,
            field_title="ظرفیت",
        )

    @field_validator("current_load", mode="before")
    @classmethod
    def _normalize_current_load(cls, value: Any) -> int:
        normalized_value = value if value is not None else 0
        normalized = _normalize_int(
            normalized_value,
            allow_zero=True,
            field_title="بار جاری",
        )
        return normalized

    @field_validator("alias_code", mode="before")
    @classmethod
    def _normalize_alias_code(cls, value: Any) -> Optional[str]:
        if value in {None, "", []}:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("manager_id", mode="before")
    @classmethod
    def _normalize_manager_id(cls, value: Any) -> Optional[int]:
        if value in {None, "", []}:
            return None
        normalized = _normalize_optional_int(value, "شناسه مدیر")
        if normalized is not None and normalized < 0:
            raise ValueError("شناسه مدیر باید نامنفی باشد")
        return normalized

    @field_validator("allowed_groups", "allowed_centers", "schools", mode="before")
    @classmethod
    def _normalize_code_sets(cls, value: Any, field: str) -> FrozenSet[int]:
        field_map = {
            "allowed_groups": "گروه‌های مجاز",
            "allowed_centers": "مراکز مجاز",
            "schools": "مدارس مجاز",
        }
        return _normalize_code_collection(value, field_map.get(field, field))

    @field_validator("is_active", mode="before")
    @classmethod
    def _validate_is_active(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        raise ValueError("وضعیت فعال باید بولی باشد")

    @model_validator(mode="after")
    def _check_business_rules(self) -> "Mentor":
        if self.capacity < 0:
            raise ValueError("ظرفیت نمی‌تواند منفی باشد")
        if self.current_load < 0:
            raise ValueError("بار جاری نمی‌تواند منفی باشد")
        if self.current_load > self.capacity:
            raise ValueError("بار جاری نمی‌تواند از ظرفیت بیشتر باشد")
        if self.type == "school" and not self.schools:
            raise ValueError("پشتیبان مدرسه باید حداقل یک مدرسه داشته باشد")
        return self

    @computed_field(return_type=int)
    def remaining_capacity(self) -> int:
        """Return the remaining capacity ensuring non-negative results."""

        return max(self.capacity - self.current_load, 0)

    @computed_field(return_type=float)
    def occupancy(self) -> float:
        """Return the current occupancy ratio within ``[0, 1]``."""

        if self.capacity == 0:
            return 1.0
        return self.current_load / self.capacity

    def to_dict(self) -> dict[str, Any]:
        """Serialize the model using Persian aliases while omitting ``None`` values."""

        return self.model_dump(by_alias=True, exclude_none=True)


# ----------------------------- Pytest test cases -----------------------------


def _build_base_payload() -> dict[str, Any]:
    return {
        "mentor_id": "101",
        "gender": "1",
        "type": "ordinary",
        "capacity": 80,
        "current_load": 10,
        "is_active": True,
    }


def test_default_capacity_and_remaining_capacity() -> None:
    data = {
        "mentor_id": 5,
        "gender": 0,
        "type": "ordinary",
        "current_load": 0,
        "is_active": True,
    }
    mentor = Mentor(**data)
    assert mentor.capacity == 60
    assert mentor.remaining_capacity == 60
    assert mentor.occupancy == 0.0


def test_zero_capacity_sets_full_occupancy() -> None:
    data = {
        "mentor_id": "77",
        "gender": 1,
        "type": "ordinary",
        "capacity": 0,
        "current_load": 0,
        "is_active": True,
    }
    mentor = Mentor(**data)
    assert mentor.occupancy == 1.0


def test_current_load_exceeding_capacity_raises_error() -> None:
    data = _build_base_payload()
    data["current_load"] = 90
    data["capacity"] = 80
    with pytest.raises(ValidationError):
        Mentor(**data)


def test_school_type_requires_non_empty_schools() -> None:
    data = _build_base_payload()
    data.update({"type": "school", "schools": []})
    with pytest.raises(ValidationError):
        Mentor(**data)


def test_code_collections_normalization_and_deduplication() -> None:
    data = _build_base_payload()
    data.update(
        {
            "allowed_groups": ["1", "001", 1],
            "allowed_centers": ("2", "02"),
            "schools": {"283", "650", 650},
        }
    )
    mentor = Mentor(**data)
    assert mentor.allowed_groups == frozenset({1})
    assert mentor.allowed_centers == frozenset({2})
    assert mentor.schools == frozenset({283, 650})


def test_persian_aliases_parsing_and_serialization() -> None:
    data = {
        "کد پشتیبان": "202",
        "جنسیت": "1",
        "نوع پشتیبان": "ordinary",
        "ظرفیت": "60",
        "بار جاری": "5",
        "فعال": True,
    }
    mentor = Mentor(**data)
    serialized = mentor.to_dict()
    assert serialized["کد پشتیبان"] == 202
    assert serialized["ظرفیت"] == 60
    assert "شناسه مدیر" not in serialized


def test_is_active_false_and_gender_validation() -> None:
    data = _build_base_payload()
    data["is_active"] = False
    mentor = Mentor(**data)
    assert mentor.is_active is False

    data_bad_gender = _build_base_payload()
    data_bad_gender["gender"] = 2
    with pytest.raises(ValidationError) as exc_info:
        Mentor(**data_bad_gender)
    assert "مقدار جنسیت نامعتبر است" in str(exc_info.value)


def test_school_type_with_valid_schools() -> None:
    mentor = Mentor(
        mentor_id="303",
        gender=1,
        type="school",
        schools=[283, "650"],
        is_active=True,
    )
    assert mentor.schools == frozenset({283, 650})
    assert mentor.remaining_capacity == 60


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    import pytest
    import sys

    raise SystemExit(pytest.main([__file__] + sys.argv[1:]))

