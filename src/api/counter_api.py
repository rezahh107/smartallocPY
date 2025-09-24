"""Public API facade for assigning counters."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from src.domain.counter.service import (
    CounterService,
    CounterServiceError,
    CounterValidationError,
    YEAR_CODE_REGEX,
)


@dataclass
class AssignCounterResponse:
    """Response envelope returned by :func:`assign_counter`."""

    ok: bool
    payload: dict[str, Any]


def assign_counter(
    service: CounterService,
    national_id: str,
    gender: Literal[0, 1],
    year_code: str,
) -> AssignCounterResponse:
    """Assign a counter through the provided service.

    The API ensures that pre-existing counters cannot be overridden by the caller.
    """

    if not isinstance(year_code, str) or not YEAR_CODE_REGEX.fullmatch(year_code):
        error = CounterValidationError(
            code="E_YEAR_CODE_INVALID",
            message_fa="کد سال تحصیلی باید شامل دو رقم باشد.",
            details={"year_code": str(year_code)},
        )
        return AssignCounterResponse(ok=False, payload=error.to_payload())

    authoritative_year = service.year_provider.current_year_code()
    if authoritative_year != year_code:
        error = CounterValidationError(
            code="E_YEAR_CODE_INVALID",
            message_fa="کد سال تحصیلی با منبع معتبر همخوانی ندارد.",
            details={"expected": authoritative_year, "received": year_code},
        )
        return AssignCounterResponse(ok=False, payload=error.to_payload())

    try:
        counter = service.get_or_create(national_id=national_id, gender=gender)
    except CounterServiceError as exc:
        return AssignCounterResponse(ok=False, payload=exc.to_payload())
    return AssignCounterResponse(ok=True, payload={"counter": counter})
