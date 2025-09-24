from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from src.domain.counter.ports import COUNTER_PREFIX
from src.domain.counter.service import COUNTER_REGEX


def build_counter(year: str, gender: int, seq: int) -> str:
    prefix = COUNTER_PREFIX[gender]
    return f"{year}{prefix}{seq:04d}"


@given(
    year=st.integers(min_value=0, max_value=99),
    gender=st.sampled_from([0, 1]),
    seq=st.integers(min_value=1, max_value=9999),
)
def test_counter_format_invariant(year: int, gender: int, seq: int) -> None:
    counter = build_counter(f"{year:02d}", gender, seq)
    assert COUNTER_REGEX.fullmatch(counter)
