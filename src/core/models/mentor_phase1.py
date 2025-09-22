# Temporary compatibility shim for legacy imports.
from .mentor import *  # noqa: F401,F403
import warnings as _w

from .mentor_phase1_legacy import (
    Mentor as _LegacyMentor,
    _encode_collections as _legacy_encode_collections,
    _normalize_code_collection as _legacy_normalize_code_collection,
    _normalize_int as _legacy_normalize_int,
    _normalize_optional_int as _legacy_normalize_optional_int,
)

_w.warn(
    "src.core.models.mentor_phase1 منسوخ شده است؛ از src.core.models.mentor استفاده کنید.",
    DeprecationWarning,
    stacklevel=2,
)

Mentor = _LegacyMentor
_encode_collections = _legacy_encode_collections
_normalize_code_collection = _legacy_normalize_code_collection
_normalize_int = _legacy_normalize_int
_normalize_optional_int = _legacy_normalize_optional_int

__all__ = [
    name
    for name in globals()
    if not name.startswith("_")
]
