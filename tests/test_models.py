from __future__ import annotations

import itertools
from pathlib import Path
import threading
import sys

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.models.mentor import AvailabilityStatus, Mentor
from src.core.models.shared_normalize import (
    PERSIAN_DIGIT_VARIANTS,
    canonicalize_mobile,
    canonicalize_national_id,
    unify_digits,
    validate_iran_national_id,
)
from src.core.models.student import Student
from src.core.special_schools import get_special_schools, is_frozen
from tests.utils.special_schools_testtools import temporary_special_schools


def build_valid_national_id(prefix: str = "001234567") -> str:
    """Return a valid Iranian national ID for testing purposes."""

    digits = [int(char) for char in prefix]
    total = sum(digit * (10 - index) for index, digit in enumerate(digits))
    remainder = total % 11
    check_digit = remainder if remainder < 2 else 11 - remainder
    return f"{prefix}{check_digit}"


def student_payload(**overrides: object) -> dict[str, object]:
    """Create a canonical student payload with overrides."""

    payload: dict[str, object] = {
        "nationalCode": build_valid_national_id(),
        "mobilePhone": "۰۹۱۲۳۴۵۶۷۸۹",
        "genderCode": "۱",
        "reg_status": "۱",
        "center": "۱",
        "edu_status": "۱",
        "grp": "۲۲",
        "schoolId": "۲۸۳",
    }
    payload.update(overrides)
    return payload


def mentor_payload(**overrides: object) -> dict[str, object]:
    """Create a canonical mentor payload with overrides."""

    payload: dict[str, object] = {
        "mentor_id": 1001,
        "first_name": "زهرا",
        "last_name": "احمدی",
        "gender": 1,
        "type": "عادی",
        "alias": "1234",
        "allowed_groups": ["۲۲", "۲۵"],
        "allowed_centers": [0, 1],
        "current_load": "0",
        "capacity": "",
        "mobile": "۰۹۱۲۳۴۵۶۷۸۹",
        "national_id": build_valid_national_id("123456789"),
    }
    payload.update(overrides)
    return payload


def test_temporary_special_schools_restores_state() -> None:
    original_codes = get_special_schools()
    original_frozen = is_frozen()

    with temporary_special_schools({777}, 1404):
        assert get_special_schools() == frozenset({777})
        assert is_frozen() is True

    assert get_special_schools() == original_codes
    assert is_frozen() == original_frozen


def test_special_schools_override_restores_after_exception(
    special_schools_override,
) -> None:
    original_codes = get_special_schools()
    original_frozen = is_frozen()

    with pytest.raises(RuntimeError, match="boom"):
        with special_schools_override({888}, 1405):
            assert get_special_schools() == frozenset({888})
            assert is_frozen() is True
            raise RuntimeError("boom")

    assert get_special_schools() == original_codes
    assert is_frozen() == original_frozen


def test_temporary_special_schools_nested_contexts() -> None:
    original_codes = get_special_schools()
    original_frozen = is_frozen()

    with temporary_special_schools({901}, 1406):
        assert get_special_schools() == frozenset({901})
        with temporary_special_schools({902, 903}, 1407):
            assert get_special_schools() == frozenset({902, 903})
        assert get_special_schools() == frozenset({901})

    assert get_special_schools() == original_codes
    assert is_frozen() == original_frozen


@pytest.mark.parametrize(
    "invalid_codes",
    [
        [0],
        [-1],
        ["0"],
        [""],
        [None],
        ["x"],
    ],
)
def test_temporary_special_schools_rejects_invalid_codes(invalid_codes: list[object]) -> None:
    with pytest.raises(ValueError, match="کد مدرسه باید عددی بزرگتر از صفر باشد"):
        with temporary_special_schools(invalid_codes, 1404):
            pass


def test_temporary_special_schools_rejects_empty_collection() -> None:
    with pytest.raises(ValueError, match="لیست مدارس ویژه نمی‌تواند خالی باشد"):
        with temporary_special_schools([], 1404):
            pass


def test_special_schools_override_fixture_usage(special_schools_override) -> None:
    original_codes = get_special_schools()
    original_frozen = is_frozen()

    with special_schools_override({910}, 1408):
        assert get_special_schools() == frozenset({910})
        assert is_frozen() is True

    assert get_special_schools() == original_codes
    assert is_frozen() == original_frozen


def test_temporary_special_schools_thread_safety() -> None:
    original_codes = get_special_schools()
    original_frozen = is_frozen()
    results: list[tuple[frozenset[int], bool]] = []

    def reader() -> None:
        results.append((get_special_schools(), is_frozen()))

    with temporary_special_schools({915}, 1410):
        worker = threading.Thread(target=reader)
        worker.start()
        worker.join()
        assert results
        codes_snapshot, frozen_snapshot = results[0]
        assert codes_snapshot == frozenset({915})
        assert frozen_snapshot is True

    assert get_special_schools() == original_codes
    assert is_frozen() == original_frozen


def test_student_alias_ingestion_and_normalization() -> None:
    student = Student.model_validate(student_payload())
    assert student.national_id == build_valid_national_id()
    assert student.mobile == "09123456789"
    assert student.gender == 1
    assert student.student_type == 1
    serialized = student.model_dump(by_alias=False)
    assert "national_id" in serialized and "nationalCode" not in serialized


def test_student_national_id_all_equal_digits_error() -> None:
    payload = student_payload(nationalCode="۱۱۱۱۱۱۱۱۱۱")
    with pytest.raises(ValueError, match="کد ملی نامعتبر است"):
        Student.model_validate(payload)


def test_student_national_id_checksum_error() -> None:
    invalid_id = build_valid_national_id()[:-1] + "0"
    payload = student_payload(nationalCode=invalid_id)
    with pytest.raises(ValueError, match="کد ملی نامعتبر است"):
        Student.model_validate(payload)


def test_student_mobile_invalid_formats_raise_error() -> None:
    payload = student_payload(mobilePhone="0912")
    with pytest.raises(ValueError, match="شماره موبایل باید با 09 شروع شده و ۱۱ رقم باشد"):
        Student.model_validate(payload)


def test_student_type_derivation_outside_special_school() -> None:
    student = Student.model_validate(student_payload(schoolId="999"))
    assert student.student_type == 0
    assert student.school_code == 999


def test_student_type_derivation_without_school_code() -> None:
    student = Student.model_validate(student_payload(schoolId=""))
    assert student.student_type == 0
    assert student.school_code is None


def test_student_group_code_zero_error() -> None:
    payload = student_payload(grp="0")
    with pytest.raises(ValueError, match="کد گروه باید بزرگتر از صفر باشد"):
        Student.model_validate(payload)


def test_student_reg_center_invalid_error() -> None:
    payload = student_payload(center="5")
    with pytest.raises(ValueError, match="مرکز ثبت نام باید یکی از مقادیر {۰، ۱، ۲} باشد"):
        Student.model_validate(payload)


def test_mentor_alias_ingestion_and_defaults() -> None:
    mentor = Mentor.model_validate(mentor_payload())
    assert mentor.capacity == 60
    assert mentor.current_load == 0
    assert mentor.allowed_groups == frozenset({22, 25})
    assert mentor.allowed_centers == frozenset({0, 1})
    assert mentor.mobile == "09123456789"
    assert mentor.national_id == build_valid_national_id("123456789")
    serialized = mentor.model_dump(by_alias=False)
    assert "alias_code" in serialized and "alias" not in serialized


def test_mentor_name_required_error() -> None:
    with pytest.raises(ValueError, match="نام و نام خانوادگی الزامی است"):
        Mentor.model_validate(mentor_payload(first_name=""))


def test_mentor_invalid_national_id_error() -> None:
    invalid = build_valid_national_id("123456789")[:-1] + "0"
    with pytest.raises(ValueError, match="کد ملی نامعتبر است"):
        Mentor.model_validate(mentor_payload(national_id=invalid))


def test_mentor_allowed_groups_empty_error() -> None:
    payload = mentor_payload(allowed_groups=[])
    with pytest.raises(ValueError, match="لیست گروه‌های مجاز نمی‌تواند خالی باشد"):
        Mentor.model_validate(payload)


def test_mentor_allowed_groups_negative_member_error() -> None:
    payload = mentor_payload(allowed_groups=["-1", "10"])
    with pytest.raises(ValueError, match="کد گروه باید عدد صحیح مثبت باشد"):
        Mentor.model_validate(payload)


def test_mentor_allowed_centers_invalid_member_error() -> None:
    payload = mentor_payload(allowed_centers=[0, 5])
    with pytest.raises(ValueError, match="مرکز مجاز باید یکی از {۰، ۱، ۲} باشد"):
        Mentor.model_validate(payload)


def test_school_mentor_requires_special_school_codes() -> None:
    payload = mentor_payload(type="مدرسه", special_schools=[])
    with pytest.raises(ValueError, match="منتور مدرسه باید حداقل یک مدرسه ویژه داشته باشد"):
        Mentor.model_validate(payload)


def test_mentor_current_load_exceeds_capacity_error() -> None:
    payload = mentor_payload(capacity="5", current_load="6")
    with pytest.raises(ValueError, match="تعداد تخصیص‌ها نمی‌تواند از ظرفیت بیشتر باشد"):
        Mentor.model_validate(payload)


def test_mentor_capacity_boundary_acceptance() -> None:
    payload = mentor_payload(capacity="5", current_load="4")
    mentor = Mentor.model_validate(payload)
    assert mentor.capacity == 5
    assert mentor.current_load == 4


def test_mentor_capacity_boundary_rejects_acceptance_when_full() -> None:
    payload = mentor_payload(capacity="5", current_load="5")
    mentor = Mentor.model_validate(payload)
    student = Student.model_validate(student_payload(group_code="۲۵", schoolId="999"))
    assert not mentor.can_accept_student(student)


def test_mentor_current_load_defaults_to_zero() -> None:
    mentor = Mentor.model_validate(mentor_payload(current_load=""))
    assert mentor.current_load == 0


def test_mentor_alias_blank_to_none() -> None:
    mentor = Mentor.model_validate(mentor_payload(alias=""))
    assert mentor.alias_code is None


def test_special_school_limit_enforced() -> None:
    payload = mentor_payload(
        type="مدرسه",
        special_schools=[101, 102, 103, 104, 105],
        allowed_centers=[0],
        allowed_groups=["۲۲"],
    )
    with pytest.raises(ValueError, match="حداکثر چهار مدرسه ویژه مجاز است"):
        Mentor.model_validate(payload)


def test_mentor_can_accept_student_respects_availability() -> None:
    mentor = Mentor.model_validate(
        mentor_payload(availability_status=AvailabilityStatus.FULL.value)
    )
    student = Student.model_validate(student_payload(schoolId="999"))
    assert not mentor.can_accept_student(student)


def test_mentor_can_accept_student_respects_centers() -> None:
    mentor = Mentor.model_validate(mentor_payload(allowed_centers=[0]))
    student = Student.model_validate(student_payload(center="۲", schoolId="999"))
    assert not mentor.can_accept_student(student)


def test_school_mentor_requires_matching_student_school() -> None:
    mentor = Mentor.model_validate(
        mentor_payload(type="مدرسه", special_schools=[283], allowed_centers=[1])
    )
    student = Student.model_validate(student_payload(schoolId="۲۸۴"))
    assert not mentor.can_accept_student(student)


def test_school_mentor_requires_school_membership() -> None:
    mentor = Mentor.model_validate(
        mentor_payload(type="مدرسه", special_schools=[650], allowed_centers=[1])
    )
    student = Student.model_validate(student_payload(schoolId="۲۸۳"))
    assert not mentor.can_accept_student(student)


def test_school_mentor_rejects_graduate_student() -> None:
    mentor = Mentor.model_validate(
        mentor_payload(type="مدرسه", special_schools=[283], allowed_centers=[1])
    )
    student = Student.model_validate(student_payload(edu_status="۰"))
    assert not mentor.can_accept_student(student)


def test_normal_mentor_rejects_special_student() -> None:
    mentor = Mentor.model_validate(mentor_payload())
    student = Student.model_validate(student_payload())
    assert not mentor.can_accept_student(student)


def test_mentor_rejects_unapproved_group() -> None:
    mentor = Mentor.model_validate(mentor_payload(allowed_groups=["۲۲"]))
    student = Student.model_validate(student_payload(group_code="۲۵", schoolId="999"))
    assert not mentor.can_accept_student(student)


def test_mentor_rejects_gender_mismatch() -> None:
    mentor = Mentor.model_validate(mentor_payload(gender=0))
    student = Student.model_validate(student_payload(genderCode="۱", schoolId="999"))
    assert not mentor.can_accept_student(student)


def test_mentor_can_accept_student_happy_path() -> None:
    mentor = Mentor.model_validate(mentor_payload(allowed_centers=[1], allowed_groups=["۲۲", "۲۵"]))
    student = Student.model_validate(student_payload(group_code="۲۲", center="۱", schoolId="999"))
    assert mentor.can_accept_student(student)


def test_shared_digit_normalization_between_models() -> None:
    raw_mobile = "۰۹۱۲٣۴۵۶۷۸۹"
    canonical = canonicalize_mobile(raw_mobile, "شماره موبایل باید با 09 شروع شده و ۱۱ رقم باشد")
    mentor = Mentor.model_validate(mentor_payload(mobile=raw_mobile))
    student = Student.model_validate(student_payload(mobilePhone=raw_mobile))
    assert unify_digits("۱۲٣۴۵") == "12345"
    assert mentor.mobile == canonical == student.mobile


def test_mentor_model_dump_canonical_fields() -> None:
    mentor = Mentor.model_validate(mentor_payload())
    dumped = mentor.model_dump(by_alias=False)
    assert dumped["allowed_groups"] == [22, 25]
    assert dumped["allowed_centers"] == [0, 1]


def test_student_model_dump_canonical_fields() -> None:
    student = Student.model_validate(student_payload())
    dumped = student.model_dump(by_alias=False)
    assert dumped["group_code"] == 22
    assert dumped["reg_center"] == 1


@st.composite
def mobile_inputs(draw: st.DrawFn) -> str:
    suffix_digits = draw(st.lists(st.integers(min_value=0, max_value=9), min_size=9, max_size=9))
    ascii_number = "09" + "".join(str(digit) for digit in suffix_digits)
    variant_number = "".join(
        draw(st.sampled_from(tuple(PERSIAN_DIGIT_VARIANTS[ch]))) for ch in ascii_number
    )
    prefix_choice = draw(st.sampled_from(["", "+98", "0098", "98"]))
    if prefix_choice:
        prefix_chars = []
        for character in prefix_choice:
            if character.isdigit():
                prefix_chars.append(
                    draw(st.sampled_from(tuple(PERSIAN_DIGIT_VARIANTS[character])))
                )
            else:
                prefix_chars.append(character)
        number_body = variant_number[1:]
        text = "".join(prefix_chars) + number_body
    else:
        text = variant_number
    separators = draw(
        st.lists(st.sampled_from(["", " ", "-", "   "]), min_size=len(text), max_size=len(text))
    )
    return "".join(itertools.chain.from_iterable(zip(text, separators, strict=True)))


@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
@given(mobile_inputs())
def test_mobile_property_based_normalization(raw: str) -> None:
    canonical = canonicalize_mobile(raw, "شماره موبایل باید با 09 شروع شده و ۱۱ رقم باشد")
    assert canonical.startswith("09")
    assert len(canonical) == 11


@st.composite
def national_id_inputs(draw: st.DrawFn) -> str:
    digits = draw(st.lists(st.integers(min_value=0, max_value=9), min_size=10, max_size=10))
    characters = [draw(st.sampled_from(tuple(PERSIAN_DIGIT_VARIANTS[str(digit)]))) for digit in digits]
    return "".join(characters)


@settings(max_examples=75, suppress_health_check=[HealthCheck.too_slow])
@given(national_id_inputs())
def test_random_national_ids_rejected_or_normalized(raw: str) -> None:
    normalized = canonicalize_national_id(
        raw,
        error_message="کد ملی باید دقیقاً ۱۰ رقم باشد",
    )
    is_valid = validate_iran_national_id(normalized)
    if not is_valid:
        with pytest.raises(ValueError, match="کد ملی نامعتبر است"):
            Student.model_validate(student_payload(nationalCode=raw))
    else:
        student = Student.model_validate(student_payload(nationalCode=raw))
        assert student.national_id == normalized

