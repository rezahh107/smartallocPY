# Student Allocation System

![CI](https://github.com/smartallocPY/smartallocPY/actions/workflows/ci.yml/badge.svg?branch=main)

A modular Python project for managing student-to-mentor allocations. The project is structured around clear layers for models, services, utilities, API endpoints, and configuration files.

## Project Structure

```
student-allocation-system/
├── src/
│   ├── core/
│   │   ├── models/
│   │   ├── services/
│   │   └── utils/
│   ├── api/
│   │   └── endpoints/
│   └── config/
├── tests/
│   ├── unit/
│   └── integration/
├── data/
│   ├── sample/
│   └── config/
```

## Getting Started

1. Create and populate an `.env` file based on `.env.example`.
2. Install dependencies using `pip install -r requirements.txt`.
3. Run unit tests with `pytest`.
4. Start the API by running `uvicorn src.api.main:app --reload`.

## Features

- Pydantic models for students, mentors, assignments, managers, and schools.
- Utility helpers for normalising phone numbers and Persian text.
- Allocation service for pairing students with mentors.
- REST API built with FastAPI exposing allocation and health endpoints.
- Configuration management via environment variables using Pydantic settings.

## Migration

The legacy phase-one mentor module has been fully replaced by the canonical `src.core.models.mentor` module. Import mentor types via `from src.core.models.mentor import Mentor, MentorType, AvailabilityStatus` going forward.

```python
from src.core.models.mentor import Mentor, MentorType

mentor = Mentor(
    mentor_id=101,
    first_name="Example",
    last_name="Mentor",
    gender=1,
    mentor_type=MentorType.NORMAL,
    manager_id=42,
    special_schools={10, 20},
    allowed_groups={7, 8},
)

mentor_dict = mentor.to_dict()
# mentor_dict["special_schools"] == [10, 20]
# mentor_dict["allowed_groups"] == [7, 8]
```

## Development

- `tests/unit` contains isolated unit tests.
- `tests/integration` contains flow-based integration tests.
- Sample data and configuration files are stored in `data/`.
- Track spec mismatches via `docs/TODOs_phase2.md`; refresh the list with `git grep -n "TODO(spec-mismatch)"`.

### Testing & Coverage
- Run tests: `pytest -q`
- Enforced coverage: ≥90% on `src/core/models/mentor.py`
- CI uploads `reports/coverage.xml` and `reports/junit.xml` as artifacts.

## License

This project is provided as-is for educational purposes.
