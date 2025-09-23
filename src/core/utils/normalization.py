"""Normalization helpers shared between student and mentor models."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Any, FrozenSet, Iterable as IterableType, Optional

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
_INT_PATTERN = re.compile(r"^[+-]?\d+$")
_NON_DIGIT_RE = re.compile(r"\D+")
_MOBILE_PATTERN = re.compile(r"^09\d{9}$")


def normalize_text(value: Any) -> str:
    """Return a whitespace-stripped textual representation of ``value``.

    Args:
        value: Arbitrary input supplied by upstream ETL systems.

    Returns:
        str: Normalized string using Unicode NFKC normalization.

    Examples:
        >>> normalize_text("  علی \u200cرضایی\n")
        'علی ‌رضایی'
    """

    if value is None:
        return ""
    return unicodedata.normalize("NFKC", str(value)).strip()


def unify_digits(value: Any) -> str:
    """Translate Persian and Arabic-Indic digits within ``value`` to ASCII.

    Args:
        value: Input that potentially contains localized digits.

    Returns:
        str: Digit-normalized string preserving non-digit characters.

    Examples:
        >>> unify_digits("۱۲۳-٤٥٦")
        '123-456'
    """

    text = normalize_text(value)
    return text.translate(_DIGIT_TRANSLATION)


def digits_only(value: Any) -> str:
    """Extract ASCII digits from ``value`` after digit unification.

    Args:
        value: Input containing numeric characters possibly mixed with text.

    Returns:
        str: String containing only ASCII digits.

    Examples:
        >>> digits_only("کد ۱۲۳۴۵")
        '12345'
    """

    return _NON_DIGIT_RE.sub("", unify_digits(value))


def parse_int(
    value: Any,
    *,
    error_message: str,
    allow_zero: bool = True,
    positive_only: bool = False,
    allow_none: bool = False,
    allowed_values: FrozenSet[int] | None = None,
    none_if_zero: bool = False,
) -> Optional[int]:
    """Parse ``value`` into an integer with extensive normalization.

    Args:
        value: Raw input received from serialization layers.
        error_message: Persian error message to raise on invalid values.
        allow_zero: Whether ``0`` is accepted as a valid number.
        positive_only: Enforce strictly positive integers when ``True``.
        allow_none: Return ``None`` when the input is empty or ``None``.
        allowed_values: Optional set restricting the resulting integer.
        none_if_zero: Convert zero values to ``None`` when enabled.

    Returns:
        Optional[int]: Normalized integer or ``None`` when permitted.

    Raises:
        ValueError: If normalization fails or constraints are violated.

    Examples:
        >>> parse_int(" ۱۲۳ ", error_message="مقدار نامعتبر است")
        123
        >>> parse_int("۰", error_message="مثبت", positive_only=True)
        Traceback (most recent call last):
        ...
        ValueError: مثبت
    """

    if value is None:
        if allow_none:
            return None
        raise ValueError(error_message)

    normalized = unify_digits(value)
    if normalized == "":
        if allow_none:
            return None
        raise ValueError(error_message)
    if not _INT_PATTERN.fullmatch(normalized):
        raise ValueError(error_message)

    result = int(normalized)
    if none_if_zero and result == 0:
        return None
    if positive_only and result <= 0:
        raise ValueError(error_message)
    if not allow_zero and result == 0:
        raise ValueError(error_message)
    if allowed_values is not None and result not in allowed_values:
        raise ValueError(error_message)
    return result


def canonicalize_national_id(value: Any, *, error_message: str) -> str:
    """Normalize an Iranian national ID to a ten-digit ASCII string.

    Args:
        value: Raw identifier potentially containing localized digits.
        error_message: Persian message emitted when normalization fails.

    Returns:
        str: Ten-digit canonical representation.

    Raises:
        ValueError: If the value cannot be converted to ten digits.

    Examples:
        >>> canonicalize_national_id("۰۱۲۳۴۵۶۷۸۹", error_message="کد ملی")
        '0123456789'
    """

    digits = digits_only(value)
    if len(digits) != 10:
        raise ValueError(error_message)
    return digits


def validate_iran_national_id(code: str) -> bool:
    """Return ``True`` when ``code`` satisfies the Iranian checksum rule.

    Args:
        code: Canonical ten-digit Iranian national ID.

    Returns:
        bool: ``True`` when the checksum and repetition rules are satisfied.

    Examples:
        >>> validate_iran_national_id("1111111111")
        False
    """

    if len(code) != 10 or not code.isdigit():
        return False
    if code == code[0] * 10:
        return False
    digits_list = [int(char) for char in code]
    total = sum(digits_list[index] * (10 - index) for index in range(9))
    remainder = total % 11
    expected = remainder if remainder < 2 else 11 - remainder
    return digits_list[-1] == expected


def canonicalize_mobile(
    value: Any,
    *,
    required: bool,
    error_message: str,
) -> Optional[str]:
    """Normalize Iranian mobile numbers to the ``09XXXXXXXXX`` format.

    Args:
        value: Raw mobile number supporting +98/0098/98 prefixes.
        required: When ``True`` missing values trigger ``ValueError``.
        error_message: Persian message for invalid numbers.

    Returns:
        Optional[str]: Canonical mobile number or ``None`` for empty optionals.

    Raises:
        ValueError: If normalization fails or requirements are not met.

    Examples:
        >>> canonicalize_mobile("+98 912 345 6789", required=True, error_message="موبایل")
        '09123456789'
    """

    if value in (None, ""):
        if required:
            raise ValueError(error_message)
        return None

    text = unify_digits(value)
    if text == "":
        if required:
            raise ValueError(error_message)
        return None

    stripped = re.sub(r"[\s\-()]+", "", text)
    digits = _NON_DIGIT_RE.sub("", stripped)
    if digits.startswith("0098"):
        digits = digits[4:]
    elif digits.startswith("098"):
        digits = digits[3:]
    elif digits.startswith("98"):
        digits = digits[2:]
    if digits.startswith("0") and len(digits) > 10:
        digits = digits[1:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = f"0{digits}"
    final = digits
    if not _MOBILE_PATTERN.fullmatch(final):
        raise ValueError(error_message)
    return final


def frozenset_of_ints(
    values: Any,
    *,
    field_title: str,
    error_message: str,
    positive_only: bool = True,
    allowed_values: FrozenSet[int] | None = None,
    default: IterableType[int] | None = None,
) -> FrozenSet[int]:
    """Convert ``values`` into a deduplicated ``frozenset`` of integers.

    Args:
        values: Candidate iterable, mapping, or scalar input.
        field_title: Persian field name used in nested error messages.
        error_message: Localized message for invalid items.
        positive_only: Require strictly positive integers when ``True``.
        allowed_values: Optional whitelist enforced on all members.
        default: Sequence returned when ``values`` is empty after cleaning.

    Returns:
        FrozenSet[int]: Normalized immutable set of integers.

    Raises:
        ValueError: If any member violates normalization constraints.

    Examples:
        >>> frozenset_of_ints([" ۱ ", 2], field_title="گروه", error_message="گروه")
        frozenset({1, 2})
    """

    if values in (None, "", []):
        if default is not None:
            return frozenset(default)
        return frozenset()

    if isinstance(values, dict):
        candidates = [key for key, enabled in values.items() if enabled]
    elif isinstance(values, str):
        if values.strip() == "":
            if default is not None:
                return frozenset(default)
            return frozenset()
        candidates = [values]
    elif isinstance(values, Iterable) and not isinstance(values, (str, bytes)):
        candidates = list(values)
        if not candidates and default is not None:
            return frozenset(default)
    else:
        candidates = [values]

    normalized: set[int] = set()
    for item in candidates:
        try:
            number = parse_int(
                item,
                error_message=error_message,
                allow_zero=not positive_only,
                positive_only=positive_only,
                allowed_values=allowed_values,
            )
        except ValueError as exc:  # pragma: no cover - message rewritten below
            raise ValueError(f"{field_title}: {exc}") from exc
        if number is not None:
            normalized.add(number)

    if not normalized and default is not None:
        return frozenset(default)
    return frozenset(normalized)


__all__ = [
    "canonicalize_mobile",
    "canonicalize_national_id",
    "digits_only",
    "frozenset_of_ints",
    "normalize_text",
    "parse_int",
    "unify_digits",
    "validate_iran_national_id",
]
