"""Simple counter service used to generate sequential identifiers."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from typing import Iterator


@dataclass
class CounterService:
    """Produces sequential identifiers with an optional prefix."""

    prefix: str = ""
    start: int = 1
    _counter: Iterator[int] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._counter = count(self.start)

    def next(self) -> str:
        """Return the next identifier from the sequence."""

        value = next(self._counter)
        return f"{self.prefix}{value}"
