from __future__ import annotations

import pytest

from src.core.models.mentor import (
    _encode_collections,
    normalize_iterable_to_int_set,
    normalize_mapping_to_int_set,
)


def test_normalize_iterable_to_int_set_handles_duplicates_and_digits() -> None:
    result = normalize_iterable_to_int_set([
        " ۱۰۱ ",
        "۱۰۲",
        103,
        "۱۰۱",
    ], "کد گروه")

    assert result == frozenset({101, 102, 103})


def test_normalize_iterable_to_int_set_rejects_nested_iterables() -> None:
    with pytest.raises(ValueError) as exc_info:
        normalize_iterable_to_int_set([[1, 2]], "کد گروه")

    assert "باید فقط شامل اعداد ساده باشد" in str(exc_info.value)


def test_normalize_mapping_to_int_set_filters_truthy_keys() -> None:
    result = normalize_mapping_to_int_set(
        {
            "۱۰۱": True,
            "102": False,
            "103": 1,
        },
        "کد گروه",
    )

    assert result == frozenset({101, 103})


def test_normalize_mapping_to_int_set_rejects_empty_values() -> None:
    with pytest.raises(ValueError) as exc_info:
        normalize_mapping_to_int_set({None: True}, "کد گروه")

    assert "نمی‌تواند مقادیر تهی" in str(exc_info.value)


def test_encode_collections_recursively_transforms_sets() -> None:
    payload = {
        "groups": {3, 1, 2},
        "nested": [
            {"codes": frozenset({4, 2})},
            ({1, 3}, frozenset({5, 4})),
        ],
        "already_sorted": [1, 2, 3],
        "unsorted_list": [3, 1, 2],
    }

    encoded = _encode_collections(payload)

    assert encoded["groups"] == [1, 2, 3]
    assert encoded["nested"][0]["codes"] == [2, 4]
    assert encoded["nested"][1] == [[1, 3], [4, 5]]
    assert encoded["already_sorted"] == [1, 2, 3]
    assert encoded["unsorted_list"] == [1, 2, 3]


def test_encode_collections_is_idempotent() -> None:
    payload = {"groups": {7, 2, 5}}

    first = _encode_collections(payload)
    second = _encode_collections(first)

    assert first == second
