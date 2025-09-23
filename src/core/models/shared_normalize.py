"""Shared normalization utilities for mentor and student models."""

from __future__ import annotations

import unicodedata
from typing import Any, FrozenSet, Iterable, Iterator

PERSIAN_DIGIT_VARIANTS: dict[str, tuple[str, ...]] = {
    "0": ("0", "۰", "٠"),
    "1": ("1", "۱", "١"),
    "2": ("2", "۲", "٢"),
    "3": ("3", "۳", "٣"),
    "4": ("4", "۴", "٤"),
    "5": ("5", "۵", "٥"),
    "6": ("6", "۶", "٦"),
    "7": ("7", "۷", "٧"),
    "8": ("8", "۸", "٨"),
    "9": ("9", "۹", "٩"),
}
"""Mapping of ASCII digits to their Persian and Arabic variants."""

_DIGIT_TRANSLATION = str.maketrans(
    {
        variant: ascii_digit
        for ascii_digit, variants in PERSIAN_DIGIT_VARIANTS.items()
        for variant in variants
    }
)

_ALLOWED_MOBILE_EXTRA = {" ", "-", "_", "(", ")", "\u200c", "\u200f"}


def _normalize_text(value: Any) -> str:
    """Return the NFKC-normalized representation of ``value``.

    Args:
        value: Arbitrary value that may include Persian glyphs.

    Returns:
        str: Unicode string normalized to the NFKC form.
    """

    if value is None:
        return ""
    return unicodedata.normalize("NFKC", str(value))


def unify_digits(value: Any) -> str:
    """Convert Persian and Arabic digits to their ASCII equivalents.

    Args:
        value: Input containing digits in mixed scripts.

    Returns:
        str: Normalized text with digits ۰-۹/٠-٩ replaced by 0-9.

    Examples:
        >>> unify_digits("۱۲٣۴۵")
        '12345'
    """

    return _normalize_text(value).translate(_DIGIT_TRANSLATION)


def canonicalize_national_id(value: Any, *, error_message: str) -> str:
    """Normalize Iranian national IDs to a ten-digit ASCII form.

    Args:
        value: Raw national ID which may include localized digits.
        error_message: Persian error message raised on invalid input.

    Returns:
        str: Canonicalized ten-digit national ID.

    Raises:
        ValueError: If the input cannot be normalized to ten digits.

    Examples:
        >>> canonicalize_national_id("٠١٢٣٤٥٦٧٨٩", error_message="خطا")
        '0123456789'
    """

    text = unify_digits(value).strip()
    if not text:
        raise ValueError(error_message)
    cleaned = "".join(char for char in text if char not in {" ", "-", "\u200c", "\u200f"})
    if not cleaned:
        raise ValueError(error_message)
    if any(not char.isdigit() for char in cleaned):
        raise ValueError(error_message)
    if len(cleaned) != 10:
        raise ValueError(error_message)
    return cleaned


def validate_iran_national_id(value: str) -> bool:
    """Validate the Iranian national ID checksum algorithm.

    Args:
        value: Canonical ten-digit national ID.

    Returns:
        bool: ``True`` when the checksum is valid and digits differ.

    Examples:
        >>> validate_iran_national_id('0012345675')
        True
    """

    if len(value) != 10 or len(set(value)) == 1:
        return False
    digits = [int(char) for char in value]
    total = sum(digits[index] * (10 - index) for index in range(9))
    remainder = total % 11
    control = remainder if remainder < 2 else 11 - remainder
    return control == digits[9]


def canonicalize_mobile(value: Any, error_message: str) -> str:
    """Normalize Iranian mobile numbers to the ``09XXXXXXXXX`` format.

    Args:
        value: Raw mobile number accepting +98/0098/98 prefixes and spaces.
        error_message: Persian error message raised on invalid input.

    Returns:
        str: Canonical mobile number beginning with ``09``.

    Raises:
        ValueError: If the number cannot be normalized to eleven digits.

    Examples:
        >>> canonicalize_mobile('+۹۸۹۱۲۳۴۵۶۷۸۹', 'خطا')
        '09123456789'
    """

    text = unify_digits(value).strip()
    if not text:
        raise ValueError(error_message)
    for character in _ALLOWED_MOBILE_EXTRA:
        text = text.replace(character, "")
    if text.startswith("+"):
        text = text[1:]
    if text.startswith("0098"):
        text = text[4:]
    elif text.startswith("98") and len(text) >= 12:
        text = text[2:]
    if text.startswith("9") and len(text) == 10:
        text = f"0{text}"
    if any(not char.isdigit() for char in text):
        raise ValueError(error_message)
    if len(text) != 11 or not text.startswith("09"):
        raise ValueError(error_message)
    return text


def parse_int(
    value: Any,
    *,
    error_message: str,
    allow_none: bool = False,
    positive_only: bool = False,
    minimum: int | None = None,
    maximum: int | None = None,
    allowed_values: FrozenSet[int] | None = None,
) -> int | None:
    """Parse integers from ETL payloads while enforcing bounds.

    Args:
        value: Raw numeric value possibly containing localized digits.
        error_message: Persian error raised when parsing fails.
        allow_none: When ``True`` allows ``None`` or empty strings.
        positive_only: When ``True`` rejects zero and negative values.
        minimum: Inclusive minimum allowed value.
        maximum: Inclusive maximum allowed value.
        allowed_values: Optional whitelist of acceptable integers.

    Returns:
        Optional[int]: Parsed integer or ``None`` when permitted.

    Raises:
        ValueError: If the value violates the provided constraints.

    Examples:
        >>> parse_int('۱۲', error_message='خطا', positive_only=True)
        12
    """

    if value is None or value == "":
        if allow_none:
            return None
        raise ValueError(error_message)
    normalized = unify_digits(value).strip()
    if not normalized:
        if allow_none:
            return None
        raise ValueError(error_message)
    try:
        number = int(normalized)
    except ValueError as exc:
        raise ValueError(error_message) from exc
    if positive_only and number <= 0:
        raise ValueError(error_message)
    if minimum is not None and number < minimum:
        raise ValueError(error_message)
    if maximum is not None and number > maximum:
        raise ValueError(error_message)
    if allowed_values is not None and number not in allowed_values:
        raise ValueError(error_message)
    return number


def _ensure_iterable(value: Any) -> Iterator[Any]:
    """Yield items from ``value`` treating scalars as singletons.

    Args:
        value: Iterable or scalar input.

    Returns:
        Iterator[Any]: Iterator over the provided values.
    """

    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        yield value
        return
    for item in value:
        yield item


def frozenset_of_ints(
    value: Any,
    *,
    error_message: str,
    item_error_message: str,
    positive_only: bool,
    allow_empty: bool,
    allowed_values: FrozenSet[int] | None = None,
) -> FrozenSet[int]:
    """Coerce an iterable to a frozenset of integers with validation.

    Args:
        value: Iterable containing raw numeric members.
        error_message: Persian error raised when the collection is empty.
        item_error_message: Persian error raised for invalid members.
        positive_only: When ``True`` each member must be greater than zero.
        allow_empty: When ``False`` an empty set raises ``ValueError``.
        allowed_values: Optional whitelist restricting allowed members.

    Returns:
        FrozenSet[int]: Immutable, validated set of integers.

    Raises:
        ValueError: If validation fails for the iterable or its members.

    Examples:
        >>> frozenset_of_ints(['۱', '۲'], error_message='لیست خالی است',
        ...                   item_error_message='عدد نامعتبر', positive_only=True, allow_empty=False)
        frozenset({1, 2})
    """

    if value is None or value == "":
        if allow_empty:
            return frozenset()
        raise ValueError(error_message)
    result = []
    for item in _ensure_iterable(value):
        number = parse_int(
            item,
            error_message=item_error_message,
            positive_only=positive_only,
            allow_none=False,
            allowed_values=allowed_values,
        )
        if number is None:
            raise ValueError(item_error_message)
        result.append(number)
    if not result and not allow_empty:
        raise ValueError(error_message)
    return frozenset(result)


__all__ = [
    "PERSIAN_DIGIT_VARIANTS",
    "canonicalize_mobile",
    "canonicalize_national_id",
    "frozenset_of_ints",
    "parse_int",
    "unify_digits",
    "validate_iran_national_id",
]
