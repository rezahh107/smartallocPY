from __future__ import annotations

from src.domain.counter.ports import COUNTER_PREFIX
from src.domain.counter.service import COUNTER_REGEX


def test_prefix_map() -> None:
    assert COUNTER_PREFIX[0] == "373"
    assert COUNTER_PREFIX[1] == "357"


def test_counter_regex_matches_examples() -> None:
    assert COUNTER_REGEX.fullmatch("543730042")
    assert COUNTER_REGEX.fullmatch("543570007")
