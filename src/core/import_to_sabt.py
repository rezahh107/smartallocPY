"""Export adapter that transforms mentors into SABT-compatible DTOs."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from .models.mentor import Mentor, MentorType
from .utils.normalization import unify_digits

_ALIAS_PATTERN = re.compile(r"^\d{4}$")
_ALIAS_ERROR = "کد مستعار منتور عادی باید دقیقاً چهار رقم باشد."


class MentorSabtDTO(BaseModel):
    """Serialized representation aligned with SABT import requirements.

    Examples:
        >>> MentorSabtDTO(mentor_id=1, mentor_type="عادی", assigned_alias_code="1234")
        MentorSabtDTO(mentor_id=1, mentor_type='عادی', assigned_alias_code='1234')
    """

    mentor_id: int = Field(..., description="شناسهٔ منتور")
    mentor_type: str = Field(..., description="نوع منتور برای ثبت")
    assigned_alias_code: str = Field(..., description="کد مستعار ارسال‌شده به ثبت")


def _normalize_alias(alias: Any) -> str | None:
    """Return a trimmed alias with digits unified, or ``None`` when absent.

    Args:
        alias: Raw alias value from upstream systems.

    Returns:
        Optional[str]: Trimmed alias string or ``None``.

    Examples:
        >>> _normalize_alias(" ۰۱۲۳ ")
        '0123'
    """

    if alias in {None, ""}:
        return None
    normalized = unify_digits(alias).strip()
    return normalized or None


def to_sabt_dto(mentor: Mentor) -> MentorSabtDTO:
    """Convert a :class:`~src.core.models.mentor.Mentor` into SABT DTO format.

    Args:
        mentor: Mentor instance subject to export.

    Returns:
        MentorSabtDTO: DTO ready for the SABT import pipeline.

    Raises:
        ValueError: If alias validation fails for normal mentors.

    Examples:
        >>> mentor = Mentor(
        ...     id=7,
        ...     first_name="زهرا",
        ...     last_name="احمدی",
        ...     gender=0,
        ...     mentor_type=MentorType.SCHOOL,
        ... )
        >>> to_sabt_dto(mentor).assigned_alias_code
        '7'
    """

    normalized_alias = _normalize_alias(mentor.alias_code)
    mentor_type_value = mentor.mentor_type.value if isinstance(mentor.mentor_type, MentorType) else str(mentor.mentor_type)

    if mentor.mentor_type == MentorType.SCHOOL:
        if normalized_alias in {None, "", "0"}:
            assigned_alias = str(mentor.mentor_id)
        else:
            assigned_alias = normalized_alias
    else:
        if normalized_alias in {None, "", "0"}:
            raise ValueError(_ALIAS_ERROR)
        if not _ALIAS_PATTERN.fullmatch(normalized_alias):
            raise ValueError(_ALIAS_ERROR)
        assigned_alias = normalized_alias

    return MentorSabtDTO(
        mentor_id=mentor.mentor_id,
        mentor_type=mentor_type_value,
        assigned_alias_code=assigned_alias,
    )


__all__ = ["MentorSabtDTO", "to_sabt_dto"]
