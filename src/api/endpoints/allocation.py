"""API endpoints for student allocation operations."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ...core.models.assignment import Assignment
from ...core.models.mentor import Mentor
from ...core.models.student import Student
from ...core.services.allocation_service import AllocationError, AllocationService

router = APIRouter(prefix="/allocation", tags=["allocation"])


class AllocationRequest(BaseModel):
    students: List[Student]
    mentors: List[Mentor]


class AllocationResponse(BaseModel):
    count: int
    assignments: List[Assignment]


@router.post("/", response_model=AllocationResponse, status_code=status.HTTP_200_OK)
def create_allocation(payload: AllocationRequest) -> AllocationResponse:
    """Create allocations for the supplied students and mentors."""

    service = AllocationService()
    try:
        assignments = service.allocate(payload.students, payload.mentors)
    except AllocationError as exc:  # pragma: no cover - forwarded via HTTP layer
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AllocationResponse(count=len(assignments), assignments=assignments)
