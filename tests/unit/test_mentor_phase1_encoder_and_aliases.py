from __future__ import annotations

from typing import Any, Dict

import pytest
from pydantic import ValidationError

from src.core.models.mentor_phase1 import (
    Mentor,
    _encode_collections,
    _normalize_code_collection,
    _normalize_int,
    _normalize_optional_int,
)


def _base_payload() -> Dict[str, Any]:
    return {
        "mentor_id": "101",
        "gender": "1",
        "type": "ordinary",
        "capacity": 60,
        "current_load": 5,
        "is_active": True,
    }


def test_to_dict_idempotency_preserves_frozensets() -> None:
    payload = _base_payload()
    payload.update(
        {
            "type": "school",
            "schools": {"۲۸۳", "650"},
            "allowed_groups": {5, 3},
            "allowed_centers": frozenset({"7", 2}),
            "manager_id": "۲۳",
        }
    )
    mentor = Mentor(**payload)
    groups_before = mentor.allowed_groups
    centers_before = mentor.allowed_centers
    schools_before = mentor.schools

    first = mentor.to_dict()
    second = mentor.to_dict()

    assert first == second
    assert mentor.allowed_groups is groups_before
    assert mentor.allowed_centers is centers_before
    assert mentor.schools is schools_before
    assert first["گروه‌های مجاز"] == [3, 5]
    assert first["مراکز مجاز"] == [2, 7]
    assert first["مدارس مجاز"] == [283, 650]
    assert first["شناسه مدیر"] == 23


def test_mapping_payload_normalizes_truthy_values() -> None:
    payload = _base_payload()
    payload.update(
        {
            "type": "school",
            "schools": {"283": 1, "650": 0, "۸۸۸": False},
        }
    )
    mentor = Mentor(**payload)
    assert mentor.schools == frozenset({283})
    serialized = mentor.to_dict()
    assert serialized["مدارس مجاز"] == [283]


def test_school_type_with_empty_iterables_raises() -> None:
    payload = _base_payload()
    payload.update({"type": "school", "schools": []})
    with pytest.raises(ValidationError):
        Mentor(**payload)


def test_set_and_frozenset_inputs_emit_sorted_lists() -> None:
    payload = _base_payload()
    payload.update(
        {
            "type": "school",
            "allowed_groups": {5, 1, 3},
            "allowed_centers": frozenset({4, 2}),
            "schools": frozenset({"۶۵۰", "۲۸۳"}),
        }
    )
    mentor = Mentor(**payload)
    assert mentor.allowed_groups == frozenset({1, 3, 5})
    assert mentor.allowed_centers == frozenset({2, 4})
    assert mentor.schools == frozenset({283, 650})
    serialized = mentor.to_dict()
    assert serialized["گروه‌های مجاز"] == [1, 3, 5]
    assert serialized["مراکز مجاز"] == [2, 4]
    assert serialized["مدارس مجاز"] == [283, 650]


@pytest.mark.parametrize("alias", ["شناسه مدیر", "شناسهٔ مدیر", "شناسه‌ٔ مدیر", "کد مدیر"])
def test_manager_id_aliases_accept_persian_digits(alias: str) -> None:
    payload = _base_payload()
    payload.pop("mentor_id")
    payload.update(
        {
            "کد پشتیبان": "500",
            alias: "۲۳۴",
            "allowed_groups": ["۲۸۳", "۲۸۳"],
        }
    )
    mentor = Mentor(**payload)
    assert mentor.mentor_id == 500
    assert mentor.manager_id == 234
    assert mentor.allowed_groups == frozenset({283})
    serialized = mentor.to_dict()
    assert serialized["شناسه مدیر"] == 234
    assert serialized["گروه‌های مجاز"] == [283]


def test_already_sorted_list_passes_through_encoder() -> None:
    groups = [1, 3, 5]
    encoded = _encode_collections(groups)
    assert encoded is groups
    assert encoded == [1, 3, 5]


def test_current_load_greater_than_capacity_raises_validation_error() -> None:
    payload = _base_payload()
    payload.update({"current_load": 61, "capacity": 60})
    with pytest.raises(ValidationError):
        Mentor(**payload)


def test_valid_school_payload_remains_unchanged_after_serialization() -> None:
    payload = _base_payload()
    payload.update(
        {
            "type": "school",
            "schools": [283, "۶۵۰"],
        }
    )
    mentor = Mentor(**payload)
    serialized = mentor.to_dict()
    assert serialized["مدارس مجاز"] == [283, 650]
    assert mentor.schools == frozenset({283, 650})


@pytest.mark.parametrize(
    ("value", "allow_zero", "message"),
    [
        (None, True, "الزامی است"),
        (True, True, "باید عددی باشد"),
        ("   ", True, "نمی‌تواند خالی باشد"),
        ("abc", True, "باید شامل ارقام باشد"),
        (0, False, "باید عددی مثبت باشد"),
    ],
)
def test_normalize_int_errors(value: Any, allow_zero: bool, message: str) -> None:
    with pytest.raises(ValueError) as exc:
        _normalize_int(value, allow_zero=allow_zero, field_title="شناسه")
    assert message in str(exc.value)


def test_normalize_optional_int_behaviour() -> None:
    assert _normalize_optional_int(None, "شناسه") is None
    with pytest.raises(ValueError):
        _normalize_optional_int(True, "شناسه")
    assert _normalize_optional_int("۰", "شناسه") == 0


def test_normalize_code_collection_edge_cases() -> None:
    assert _normalize_code_collection(None, "کد") == frozenset()
    assert _normalize_code_collection({"101": True, "202": False}, "کد") == frozenset({101})
    assert _normalize_code_collection("   ", "کد") == frozenset()
    assert _normalize_code_collection([], "کد") == frozenset()
    with pytest.raises(ValueError):
        _normalize_code_collection([None], "کد")
    with pytest.raises(ValueError):
        _normalize_code_collection(["   "], "کد")
    with pytest.raises(ValueError):
        _normalize_code_collection([[1]], "کد")
    with pytest.raises(ValueError):
        _normalize_code_collection([{"v": 1}], "کد")
    with pytest.raises(ValueError):
        _normalize_code_collection([True], "کد")


def test_encode_collections_handles_mixed_types_and_tuples() -> None:
    data = {
        "set": {1, "2"},
        "list": [3, 1],
        "tuple": ({2, 1}, [3, 4]),
    }
    encoded = _encode_collections(data)
    assert encoded["set"] == [1, "2"]
    assert encoded["list"] == [1, 3]
    assert encoded["tuple"][0] == [1, 2]
    assert encoded["tuple"][1] == [3, 4]


def test_gender_and_type_validations_raise_errors() -> None:
    with pytest.raises(ValidationError):
        Mentor(**{**_base_payload(), "gender": 3})
    with pytest.raises(ValidationError):
        Mentor(**{**_base_payload(), "type": "invalid"})


def test_alias_code_trimming_and_manager_negative_rejection() -> None:
    mentor = Mentor(**{**_base_payload(), "alias_code": "  code  "})
    assert mentor.alias_code == "code"
    with pytest.raises(ValidationError):
        Mentor(**{**_base_payload(), "manager_id": -5})


def test_is_active_requires_boolean_and_capacity_rules() -> None:
    with pytest.raises(ValidationError):
        Mentor(**{**_base_payload(), "is_active": "yes"})
    with pytest.raises(ValidationError):
        Mentor(**{**_base_payload(), "capacity": -1})
    with pytest.raises(ValidationError):
        Mentor(**{**_base_payload(), "current_load": -1})


def test_occupancy_with_zero_capacity_reports_full() -> None:
    mentor = Mentor(**{**_base_payload(), "capacity": 0, "current_load": 0})
    assert mentor.occupancy == 1.0


