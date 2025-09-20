from src.core.utils.mobile_normalizer import normalize_mobile_number
from src.core.utils.persian_normalizer import normalize_persian_text


def test_normalize_mobile_number():
    assert normalize_mobile_number("۰۹۱۲-۳۴۵-۶۷۸۹") == "+989123456789"
    assert normalize_mobile_number("00989121234567") == "+989121234567"
    assert normalize_mobile_number("invalid") is None


def test_normalize_persian_text():
    assert normalize_persian_text("علي") == "علي".replace("ي", "ی")
    assert normalize_persian_text(None) is None
