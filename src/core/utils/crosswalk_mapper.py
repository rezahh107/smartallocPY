"""Utility for mapping external codes to internal identifiers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional


class CrosswalkMapper:
    """Provides lookups for translating between code systems."""

    def __init__(self, mapping: Optional[Dict[str, str]] = None) -> None:
        self._mapping: Dict[str, str] = mapping or {}

    @classmethod
    def from_json(cls, path: Path) -> "CrosswalkMapper":
        """Create a mapper from a JSON file containing key/value pairs."""

        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("Crosswalk JSON must contain an object at the root")
        return cls(mapping={str(key): str(value) for key, value in data.items()})

    def map(self, external_code: str) -> Optional[str]:
        """Return the mapped code or ``None`` if a match does not exist."""

        return self._mapping.get(str(external_code))

    def add_mapping(self, external_code: str, internal_code: str) -> None:
        """Add or update an entry in the map."""

        self._mapping[str(external_code)] = str(internal_code)

    def __contains__(self, item: str) -> bool:
        return item in self._mapping
