"""Utility helpers for normalising Iranian mobile numbers."""

from __future__ import annotations

import re
from typing import Optional

_PERSIAN_DIGITS = {
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
}


def _convert_persian_digits(value: str) -> str:
    return "".join(_PERSIAN_DIGITS.get(ch, ch) for ch in value)


def normalize_mobile_number(raw_number: Optional[str]) -> Optional[str]:
    """Normalise mobile numbers to the ``+989xxxxxxxxx`` format.

    Args:
        raw_number: User supplied mobile number in free-form text.

    Returns:
        The normalised representation or ``None`` when the input cannot be
        interpreted as a valid Iranian mobile number.
    """

    if not raw_number:
        return None

    # Replace Persian digits and remove all non-numeric characters.
    processed = _convert_persian_digits(raw_number)
    digits = re.sub(r"\D", "", processed)
    if not digits:
        return None

    if digits.startswith("0098"):
        digits = digits[2:]
    if digits.startswith("098"):
        digits = digits[1:]

    if digits.startswith("98"):
        core = digits[2:]
    elif digits.startswith("0"):
        core = digits[1:]
    else:
        core = digits

    if len(core) != 10 or not core.startswith("9"):
        return None

    return f"+98{core}"
