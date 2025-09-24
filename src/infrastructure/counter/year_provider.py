"""Concrete implementations of :class:`AcademicYearProvider`."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Callable
from zoneinfo import ZoneInfo

from src.domain.counter.ports import AcademicYearProvider
from src.domain.counter.service import CounterValidationError


@dataclass
class FixedAcademicYearProvider(AcademicYearProvider):
    """Provider returning a fixed academic year code."""

    year_code: str

    def current_year_code(self) -> str:
        return self.year_code


@dataclass
class GregorianAcademicYearProvider(AcademicYearProvider):
    """Academic year provider based on a Gregorian cut-over date."""

    cutover_month: int
    cutover_day: int
    timezone: ZoneInfo
    clock: Callable[[], datetime]

    def current_year_code(self) -> str:
        now = self.clock().astimezone(self.timezone)
        cutover = datetime.combine(
            datetime(now.year, self.cutover_month, self.cutover_day, tzinfo=self.timezone).date(),
            time(0, 0),
            tzinfo=self.timezone,
        )
        if now > cutover:
            year = now.year % 100
        else:
            year = (now.year - 1) % 100
        year_code = f"{year:02d}"
        if len(year_code) != 2:
            raise CounterValidationError(
                code="E_YEAR_CODE_INVALID",
                message_fa="کد سال تحصیلی باید شامل دو رقم باشد.",
                details={"year_code": year_code},
            )
        return year_code
