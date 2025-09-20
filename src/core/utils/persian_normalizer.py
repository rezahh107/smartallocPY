"""Utility functions for normalising Persian text input."""

from __future__ import annotations

from typing import Optional

_TRANSLATION_TABLE = str.maketrans(
    {
        "ي": "ی",
        "ك": "ک",
        "ۀ": "ه",
        "ة": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "ٱ": "ا",
    }
)


def normalize_persian_text(value: Optional[str]) -> Optional[str]:
    """Normalise Arabic variants to standard Persian characters."""

    if value is None:
        return None
    normalised = value.translate(_TRANSLATION_TABLE)
    return " ".join(segment for segment in normalised.split() if segment)
