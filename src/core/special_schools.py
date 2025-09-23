"""Thread-safe governance helpers for configuring special-school codes."""

from __future__ import annotations

from threading import RLock
from typing import FrozenSet, Iterable, Optional

from .models.constants import DEFAULT_SPECIAL_SCHOOLS
from .models.shared_normalize import frozenset_of_ints, parse_int

_SPECIAL_SCHOOLS: FrozenSet[int] = DEFAULT_SPECIAL_SCHOOLS
_FROZEN_YEAR: Optional[int] = None
_LOCK = RLock()


def get_special_schools() -> FrozenSet[int]:
    """Return the current frozen set of special-school codes.

    Returns:
        FrozenSet[int]: Immutable collection of configured school codes.

    Examples:
        >>> 283 in get_special_schools()
        True
    """

    return _SPECIAL_SCHOOLS


def is_frozen() -> bool:
    """Return ``True`` once the academic year configuration is frozen.

    Returns:
        bool: ``True`` when :func:`set_special_schools` locked the year.
    """

    return _FROZEN_YEAR is not None


def set_special_schools(codes: Iterable[int], year: int | str) -> None:
    """Freeze the special-school configuration for a specific academic year.

    Args:
        codes: Iterable of school codes expected to be positive integers.
        year: Academic year (e.g., ``1404``) tied to the configuration.

    Raises:
        ValueError: If validation fails or the year has already been frozen.
    """

    global _SPECIAL_SCHOOLS, _FROZEN_YEAR

    with _LOCK:
        normalized_year = parse_int(
            year,
            error_message="سال تحصیلی باید عددی بزرگتر از صفر باشد.",
            positive_only=True,
        )
        if normalized_year is None:
            raise ValueError("سال تحصیلی باید مشخص شود.")

        normalized_codes = frozenset_of_ints(
            codes,
            error_message="لیست مدارس ویژه نمی‌تواند خالی باشد.",
            item_error_message="کد مدرسه باید عددی بزرگتر از صفر باشد.",
            positive_only=True,
            allow_empty=False,
        )

        if _FROZEN_YEAR is None:
            _SPECIAL_SCHOOLS = normalized_codes
            _FROZEN_YEAR = normalized_year
            return

        if _FROZEN_YEAR == normalized_year and _SPECIAL_SCHOOLS == normalized_codes:
            return

        raise ValueError("پیکربندی مدارس ویژه برای این سال قبلاً ثبت شده است.")


__all__ = ["get_special_schools", "is_frozen", "set_special_schools"]
