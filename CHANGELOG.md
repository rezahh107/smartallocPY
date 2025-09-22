# Changelog

All notable changes to this project will be documented in this file.

## [0.1.1] - 2025-09-22
### Changed
- Renamed `src.core.models.mentor_phase1` to `src.core.models.mentor` as the canonical mentor model module.
- Updated the public API exports to `from src.core.models.mentor import Mentor, MentorType, AvailabilityStatus`.
- Exposed stable helper exports (`normalize_iterable_to_int_set`, `normalize_mapping_to_int_set`, `_encode_collections`) from `src.core.models.mentor`.

### Removed
- Removed the compatibility shim module that previously proxied `mentor_phase1` imports.

### Added
- Added a CI guard to prevent reintroduction of `mentor_phase1` references.

## [0.1.0] - 2024-01-01
### Added
- Initial release.
