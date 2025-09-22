from __future__ import annotations

from typing import Any, Dict

import pytest
from pydantic import ValidationError

from src.core.models.mentor import (
    AvailabilityStatus,
    Mentor,
    MentorType,
    _encode_collections,
    _normalize_code_collection,
    _normalize_int,
    _normalize_optional_int,
    normalize_iterable_to_int_set,
    normalize_mapping_to_int_set,
)


def _base_payload(**overrides: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "mentor_id": "101",
        "first_name": "  سارا ",
        "last_name": " کاظمی ",
        "gender": "1",
        "mentor_type": MentorType.NORMAL.value,
        "subject_areas": {"۱۰۱", "102", 103},
        "current_assignments": "5",
        "max_students": "60",
        "availability_status": AvailabilityStatus.AVAILABLE,
    }
    payload.update(overrides)
    return payload


def test_to_dict_idempotency_preserves_frozensets() -> None:
    payload = _base_payload(
        mentor_type=MentorType.SCHOOL.value,
        special_schools={"۲۸۳", "650"},
        subject_areas={5, "3"},
    )
    mentor = Mentor(**payload)
    groups_before = mentor.allowed_groups
    schools_before = mentor.special_schools

    first = mentor.to_dict()
    second = mentor.to_dict()

    assert mentor.allowed_groups is groups_before
    assert mentor.special_schools is schools_before
    assert first == second
    assert first["special_schools"] == [283, 650]
    assert first["subject_areas"] == [3, 5]


@pytest.mark.parametrize(
    "alias",
    ["manager_id", "شناسه مدیر", "شناسهٔ مدیر", "شناسه‌ٔ مدیر"],
)
def test_manager_id_aliases_accept_persian_digits(alias: str) -> None:
    payload = _base_payload()
    payload.pop("mentor_id")
    payload.update({"id": "500", alias: "۲۳۴", "subject_areas": ["۲۸۳", "۲۸۳"]})
    mentor = Mentor(**payload)

    assert mentor.mentor_id == 500
    assert mentor.manager_id == 234
    assert mentor.allowed_groups == frozenset({283})
    serialized = mentor.to_dict()
    assert serialized["id"] == 500
    assert serialized["subject_areas"] == [283]


def test_special_schools_validation_enforces_positive_ints() -> None:
    with pytest.raises(ValidationError):
        Mentor(
            **_base_payload(
                mentor_type=MentorType.SCHOOL.value,
                special_schools=["abc"],
            )
        )


def test_special_schools_cannot_exceed_limit() -> None:
    with pytest.raises(ValidationError) as exc:
        Mentor(
            **_base_payload(
                mentor_type=MentorType.SCHOOL.value,
                special_schools=[101, 202, 303, 404, 505],
            )
        )

    assert "حداکثر چهار مدرسه" in str(exc.value)


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


def test_normalize_iterable_helper_edge_cases() -> None:
    assert normalize_iterable_to_int_set(None, "کد") == frozenset()
    assert normalize_iterable_to_int_set("   ", "کد") == frozenset()
    assert normalize_iterable_to_int_set([], "کد") == frozenset()
    with pytest.raises(ValueError):
        normalize_iterable_to_int_set([None], "کد")
    with pytest.raises(ValueError):
        normalize_iterable_to_int_set(["   "], "کد")
    with pytest.raises(ValueError):
        normalize_iterable_to_int_set([[1]], "کد")
    with pytest.raises(ValueError):
        normalize_iterable_to_int_set([{"v": 1}], "کد")
    with pytest.raises(ValueError):
        normalize_iterable_to_int_set([True], "کد")


def test_normalize_mapping_helper_filters_enabled_entries() -> None:
    mapping = {"101": True, "202": False}
    assert normalize_mapping_to_int_set(mapping, "کد") == frozenset({101})
    # Compatibility alias remains available for any legacy imports
    assert _normalize_code_collection(mapping, "کد") == frozenset({101})


def test_current_load_greater_than_capacity_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        Mentor(**_base_payload(current_assignments=61, max_students=60))


def test_availability_status_serializes_to_value() -> None:
    mentor = Mentor(**_base_payload(availability_status=AvailabilityStatus.FULL))
    serialized = mentor.to_dict()
    assert serialized["availability_status"] == AvailabilityStatus.FULL.value


def test_workload_percentage_for_zero_capacity() -> None:
    mentor = Mentor(**_base_payload())
    zero_capacity = mentor.model_copy(update={"capacity": 0, "current_load": 0})
    assert zero_capacity.get_workload_percentage() == 0.0
    assert zero_capacity.capacity_remaining == 0


def test_mobile_normalization_variants() -> None:
    assert Mentor(**_base_payload(mobile=None)).mobile is None

    for raw in ["+989123456789", "989123456789", "9123456789", "09123456789"]:
        mentor = Mentor(**_base_payload(mobile=raw))
        assert mentor.mobile == "09123456789"


def test_invalid_mobile_number_rejected() -> None:
    with pytest.raises(ValidationError):
        Mentor(**_base_payload(mobile="12345"))


def test_manager_name_normalization_and_gender_validation() -> None:
    mentor = Mentor(**_base_payload(manager_name="  علی  "))
    assert mentor.manager_name == "علی"

    mentor_with_empty_manager = Mentor(**_base_payload(manager_name="   "))
    assert mentor_with_empty_manager.manager_name is None

    with pytest.raises(ValidationError):
        Mentor(**_base_payload(gender=3))


def test_special_school_codes_must_be_positive() -> None:
    with pytest.raises(ValidationError) as exc:
        Mentor(
            **_base_payload(
                mentor_type=MentorType.SCHOOL.value,
                special_schools=["۰"],
            )
        )

    assert "باید عدد صحیح مثبت باشد" in str(exc.value)


def test_allowed_groups_accepts_none_and_mixed_inputs() -> None:
    mentor = Mentor(**_base_payload(subject_areas=None))
    assert mentor.allowed_groups == frozenset()

    mentor = Mentor(**_base_payload(subject_areas=["۱", 2, "003"]))
    assert mentor.allowed_groups == frozenset({1, 2, 3})


def test_manager_id_normalization_handles_empty_and_negative() -> None:
    mentor = Mentor(**_base_payload(manager_id="  "))
    assert mentor.manager_id is None

    with pytest.raises(ValidationError):
        Mentor(**_base_payload(manager_id="-5"))


def test_national_id_normalization_and_validation() -> None:
    mentor = Mentor(**_base_payload(national_id="۰۰۸۴۵۷۵۹۴۸"))
    assert mentor.national_id == "0084575948"

    with pytest.raises(ValidationError):
        Mentor(**_base_payload(national_id="1234567890"))
