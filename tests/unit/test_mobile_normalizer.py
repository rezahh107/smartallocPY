from __future__ import annotations

from src.core.utils.mobile_normalizer import normalize_mobile_number


def test_normalize_mobile_number_handles_various_prefixes() -> None:
    assert normalize_mobile_number("+98 912-345-6789") == "+989123456789"
    assert normalize_mobile_number("00989123456789") == "+989123456789"
    assert normalize_mobile_number("9123456789") == "+989123456789"


def test_normalize_mobile_number_converts_persian_digits() -> None:
    assert normalize_mobile_number("۰۹۱۲۳۴۵۶۷۸۹") == "+989123456789"


def test_normalize_mobile_number_rejects_invalid_values() -> None:
    assert normalize_mobile_number(None) is None
    assert normalize_mobile_number("") is None
    assert normalize_mobile_number("12345") is None
