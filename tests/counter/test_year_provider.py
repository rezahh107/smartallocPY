from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.infrastructure.counter.year_provider import GregorianAcademicYearProvider


def make_clock(times):
    times_iter = iter(times)

    def _clock() -> datetime:
        return next(times_iter)

    return _clock


def test_year_provider_boundary_consistency() -> None:
    tz = ZoneInfo("Asia/Tehran")
    before = datetime(2024, 9, 22, 20, 30, tzinfo=ZoneInfo("UTC"))
    before_local = before.astimezone(tz)
    just_before = before_local - timedelta(minutes=5)
    provider = GregorianAcademicYearProvider(
        cutover_month=9,
        cutover_day=23,
        timezone=tz,
        clock=make_clock([just_before, before_local]),
    )
    first = provider.current_year_code()
    second = provider.current_year_code()
    assert first == second


def test_year_provider_after_cutover() -> None:
    tz = ZoneInfo("Asia/Tehran")
    after_cutover = datetime(2024, 9, 23, 0, 5, tzinfo=tz)
    provider = GregorianAcademicYearProvider(
        cutover_month=9,
        cutover_day=23,
        timezone=tz,
        clock=make_clock([after_cutover, after_cutover + timedelta(days=1)]),
    )
    assert provider.current_year_code() == provider.current_year_code()
