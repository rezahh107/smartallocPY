"""Test-only helpers for temporarily overriding special-school governance."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, ContextManager, Generator, Iterable

import pytest

from src.core.models.shared_normalize import frozenset_of_ints, parse_int
from src.core import special_schools as governance


@contextmanager
def temporary_special_schools(
    codes: Iterable[int],
    year: int | str,
) -> Generator[None, None, None]:
    """Temporarily override the SPECIAL_SCHOOLS registry for tests.

    The context manager validates incoming codes using the same normalization
    helpers as the production governance API and restores the prior state even
    if an exception occurs inside the ``with`` block.

    Args:
        codes: Iterable of school codes expected to be positive integers.
        year: Academic year tied to the temporary configuration.

    Yields:
        None: The body executes with the overridden registry in effect.

    Raises:
        ValueError: If ``codes`` or ``year`` violate validation constraints.

    Examples:
        >>> from src.core.special_schools import get_special_schools
        >>> with temporary_special_schools({901}, 1404):
        ...     assert get_special_schools() == frozenset({901})
    """

    with governance._LOCK:  # type: ignore[attr-defined]
        previous_codes = governance._SPECIAL_SCHOOLS  # type: ignore[attr-defined]
        previous_year = governance._FROZEN_YEAR  # type: ignore[attr-defined]
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
        governance._SPECIAL_SCHOOLS = normalized_codes  # type: ignore[attr-defined]
        governance._FROZEN_YEAR = normalized_year  # type: ignore[attr-defined]
    try:
        yield
    finally:
        with governance._LOCK:  # type: ignore[attr-defined]
            governance._SPECIAL_SCHOOLS = previous_codes  # type: ignore[attr-defined]
            governance._FROZEN_YEAR = previous_year  # type: ignore[attr-defined]


@pytest.fixture
def special_schools_override() -> Callable[[Iterable[int], int | str], ContextManager[None]]:
    """Provide a pytest fixture for temporarily overriding special schools.

    Returns:
        Callable[[Iterable[int], int | str], ContextManager[None]]: Factory that
            yields a context manager wrapping :func:`temporary_special_schools`.

    Examples:
        >>> def test_override(special_schools_override):
        ...     with special_schools_override({777}, 1404):
        ...         pass
    """

    def _override(codes: Iterable[int], year: int | str) -> ContextManager[None]:
        return temporary_special_schools(codes, year)

    yield _override


__all__ = ["special_schools_override", "temporary_special_schools"]
