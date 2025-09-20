# Student Allocation System

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

## Development

- `tests/unit` contains isolated unit tests.
- `tests/integration` contains flow-based integration tests.
- Sample data and configuration files are stored in `data/`.

## License

This project is provided as-is for educational purposes.
